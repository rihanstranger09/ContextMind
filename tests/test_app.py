from fastapi.testclient import TestClient
from app.main import app
from graph.store import Store
from graph.tools import Tools
from agents.company_brain import Agent
import pytest
@pytest.fixture
def store(tmp_path): return Store('demo',tmp_path/'graph.json')
def test_seed_and_resolver(store):
    t=Tools(store)
    assert t.resolve_entity('who owns gateway service?')[0]['id']=='sys_gateway'
    assert t.resolve_entity('API-Gateway')[0]['id']=='sys_gateway'
def test_impact_direct_and_multihop(store):
    paths=Tools(store).analyze_system_impact('sys_database')
    assert any(p[0]['source']=='project_mobile' and len(p)==2 for p in paths)
    assert any(p[0]['source']=='sys_gateway' and len(p)==1 for p in paths)
    assert not Tools(store).analyze_system_impact('sys_unknown')
def test_experts_include_indirect(store):
    experts=Tools(store).find_experts('sys_database')
    assert {'person_david','person_alice','person_carol'}<={e['person']['id'] for e in experts}
    assert all(e['paths'] and e['score']>0 for e in experts)
def test_decision_sources(store):
    r=Agent(store).ask('Why was Analytics Migration delayed?')
    assert r['intent']=='decision'
    assert 'replication' in r['facts'][0]['text']
    assert {'ticket_replication','message_replication'}<={s['id'] for s in r['sources']}
    assert r['graph_trace']
    assert store.get(r['id'])['type']=='AgentDecision'
def test_no_hallucination(store):
    r=Agent(store).ask('Who owns the lunar colony?')
    assert not r['facts'] and 'not have enough' in r['answer']
def test_owner_and_gap(store):
    assert any('David Brown' in f['text'] for f in Agent(store).ask('Who owns Database Cluster?')['facts'])
    assert Tools(store).knowledge_gaps()[0]['entity']['id']=='sys_redis'
def test_resolved_ticket_no_longer_blocks(store):
    t=Tools(store)
    assert t.find_project_blockers('project_analytics')
    ticket=dict(store.get('ticket_replication'));ticket['status']='RESOLVED';store.upsert(ticket,[])
    assert not t.find_project_blockers('project_analytics')
def test_upsert_idempotent(store):
    node=dict(store.get('doc_database'));count=len(store.nodes)
    store.upsert(node,[]);store.upsert(node,[])
    assert len(store.nodes)==count
    assert Store('demo',store.path).get(node['id'])==node
def test_api(store,monkeypatch):
    monkeypatch.setenv('INGEST_TOKEN','test-token')
    with TestClient(app) as client:
        app.state.store=store
        assert client.get('/').status_code==200
        assert client.get('/api/graph/subgraph?depth=9').status_code==422
        assert client.get('/api/entities/missing').status_code==404
        assert client.post('/api/chat',json={'question':'Who owns API Gateway?'}).json()['graph_trace']
        payload=dict(id='new_ticket',name='New blocker',updated_at='2026-10-09T10:00:00Z',project_id='project_payments')
        assert client.post('/api/ingest/tickets',json=payload).status_code==401
        headers={'Authorization':'Bearer test-token'}
        assert client.post('/api/ingest/tickets',json=payload,headers=headers).status_code==200
        assert client.post('/api/ingest/tickets',json=payload,headers=headers).json()['created'] is False
        payload['updated_at']='2026-09-01T10:00:00Z'
        assert client.post('/api/ingest/tickets',json=payload,headers=headers).status_code==409

def test_compound_demo_includes_decision(store):
    r=Agent(store).ask('What is at risk if the Database Cluster is unavailable, who should respond, and what previous decisions are relevant?')
    assert any('replication reliability' in f['text'] for f in r['facts'])
    assert any('Mobile App Redesign' in f['text'] for f in r['facts'])
    assert any('David Brown' in f['text'] for f in r['facts'])
    assert all(f['path_indices'] for f in r['facts'])

def test_cycle_terminates(store):
    store.add_edge(dict(source='sys_database',type='DEPENDS_ON',target='sys_gateway'))
    paths=Tools(store).analyze_system_impact('sys_database')
    assert paths and len(paths)<30

def test_seeded_relationship_change_rejected(store,monkeypatch):
    monkeypatch.setenv('INGEST_TOKEN','test-token')
    with TestClient(app) as client:
        app.state.store=store
        r=client.post('/api/ingest/tickets',headers={'Authorization':'Bearer test-token'},json=dict(id='ticket_replication',name='DB-212',updated_at='2026-10-10T12:00:00Z',about_id='sys_database',project_id='project_analytics',assignee_id='person_alice'))
        assert r.status_code==409

@pytest.mark.parametrize('path', ['/demo.html', '/demo.js', '/dashboard', '/dashboard/'])
def test_demo_routes(store, path):
    with TestClient(app) as client:
        app.state.store = store
        assert client.get(path).status_code == 200


def test_health_metadata_and_readiness(store, monkeypatch):
    with TestClient(app) as client:
        app.state.store = store
        response = client.get('/api/health')
        assert response.status_code == 200
        health = response.json()
        assert health['status'] == 'healthy'
        assert health['version'] == '1.0.0-mvp'
        assert health['graph_mode'] == health['backend'] == 'demo'
        assert health['sample_data'] == 'NovaPay'
        def unavailable(_):
            raise ConnectionError('sensitive internal host details')
        monkeypatch.setattr(store, 'get', unavailable)
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json()['status'] == 'unhealthy'
        assert 'sensitive' not in response.text


def test_health_uses_actual_backend(store):
    from unittest.mock import Mock
    with TestClient(app) as client:
        app.state.store = Mock(backend='falkordb')
        app.state.store.get.return_value = {'id': 'sys_database'}
        assert client.get('/api/health').json()['graph_mode'] == 'falkordb'
        app.state.store.get.return_value = None
        assert client.get('/api/health').status_code == 503


@pytest.mark.parametrize('question', [
    'What breaks if the Database Cluster goes down?',
    'Who should investigate an API Gateway incident?',
    'Why was Analytics Migration delayed?',
    'Find experts on Payment Service',
    'What tickets block the Q4 launch?',
])
def test_submission_demo_questions(store, question):
    with TestClient(app) as client:
        app.state.store = store
        result = client.post('/api/chat', json={'question': question}).json()
        assert result['facts']
        assert result['sources']
        assert result['graph_trace']
        assert result['graph']['nodes']
        assert result['graph']['edges']
