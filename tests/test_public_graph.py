import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from graph.store import Store, PUBLIC_SEED
from graph.ingestion import validate_snapshot, replay
from agents.public_brain import PublicAgent
from connectors.github import GitHub, clean

@pytest.fixture
def public_store(tmp_path):
    return Store('demo', tmp_path/'public.json', workspace='falkordb')


def test_snapshot_integrity():
    raw=json.loads(PUBLIC_SEED.read_text())
    validate_snapshot(raw)
    assert raw['metadata']['repository_count']>=100
    assert all(n['source_url'].startswith('https://github.com/') for n in raw['nodes'])
    assert all(not n.get('email') for n in raw['nodes'] if n['type']=='Person')
    assert not any(e['type']=='MAINTAINS' for e in raw['edges'])
    assert not any(n['type']=='Decision' for n in raw['nodes'])
    bad=copy.deepcopy(raw); bad['nodes'][0]['name']='tampered'
    with pytest.raises(ValueError,match='hash mismatch'): validate_snapshot(bad)
    bad=copy.deepcopy(raw);bad['nodes'][0]['visibility']='private'
    with pytest.raises(ValueError,match='Non-public'): validate_snapshot(bad)


def test_public_no_private_or_fictional_answers(public_store):
    a=PublicAgent(public_store)
    for q in ["What is FalkorDB's annual revenue?",'Tell me the private roadmap',
              'What is the CEO salary?', 'Why did FalkorDB choose Cypher?',
              'Which Python client version supports FalkorDB v1.0+?']:
        r=a.ask(q)
        assert not r['facts'] and not r['sources']
        assert 'not in the collected snapshot' in r['answer']
    r=a.ask('How do I get started with FalkorDB in Python?')
    assert r['resolved_entities'][0]['name']=='FalkorDB/falkordb-py'
    assert any('falkordb-py/' in n['source_url'] for n in r['sources'])


def test_activity_not_personal_ranking(public_store):
    r=PublicAgent(public_store).ask('Who maintains the Python client?')
    assert r['facts']
    assert all('score' not in f['text'] and 'best' not in f['text'] for f in r['facts'])
    assert any('not recent activity' in f['text'] for f in r['facts'])
    assert any('CODEOWNERS' in notice for notice in r['notices'])


def test_idempotent_replay_and_forget(public_store):
    replay(public_store,PUBLIC_SEED)
    before=(len(public_store.nodes),len(public_store.edges))
    replay(public_store,PUBLIC_SEED)
    assert before==(len(public_store.nodes),len(public_store.edges))
    person=public_store.search(type='Person')[0]
    public_store.forget_person(person['id'])
    replay(public_store,PUBLIC_SEED)
    assert public_store.get(person['id']) is None
    assert not public_store.adjacent(person['id'])
    reopened=Store('demo',public_store.path,workspace='falkordb')
    assert reopened.is_suppressed(person['id'])
    assert reopened.get(person['id']) is None


def test_workspace_api(public_store,tmp_path,monkeypatch):
    monkeypatch.setenv('INGEST_TOKEN','test-token')
    with TestClient(app) as client:
        app.state.public_store=public_store
        app.state.store=Store('demo',tmp_path/'nova.json')
        assert client.get('/api/entities/sys_database?workspace=falkordb').status_code==404
        assert client.get('/api/entities/org_falkordb?workspace=novapay').status_code==404
        assert client.get('/api/entities?workspace=invalid').status_code==422
        health=client.get('/api/health?workspace=falkordb').json()
        assert health['status']=='healthy' and not health['fictional_data']
        assert health['graph_mode']=='demo'  # Workspace is not storage mode.
        assert client.get('/api/coverage?workspace=falkordb').json()['shipped_snapshot']['repository_count']>=100
        person=public_store.search(type='Person')[0]
        assert client.delete('/api/people/'+person['id']).status_code==401
        r=client.delete('/api/people/'+person['id'],headers={'Authorization':'Bearer test-token'})
        assert r.status_code==200 and r.json()['suppressed_on_replay']
        assert client.get('/api/entities/'+person['id']+'?workspace=falkordb').status_code==404
        repo=public_store.search(type='Repository')[0]
        assert client.get('/api/experts/'+repo['id']+'?workspace=falkordb').status_code==422


def test_connector_guard_and_redaction():
    assert 'a@b.example' not in clean('Contact a@b.example')
    with pytest.raises(ValueError): GitHub(delay=0).get('repos/other/private')


def test_failed_validation_does_not_mutate_graph(public_store,tmp_path):
    bad=json.loads(PUBLIC_SEED.read_text());bad['edges'][0]['target']='not-present'
    f=tmp_path/'bad.json';f.write_text(json.dumps(bad))
    before=copy.deepcopy(public_store.nodes)
    with pytest.raises(ValueError): replay(public_store,f)
    assert public_store.nodes==before
