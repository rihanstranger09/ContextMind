from fastapi.testclient import TestClient
from app.main import app
from graph.showcase import CYPHER, graph_showcase
from graph.store import Store


def test_json_preview_is_not_misrepresented_as_native(tmp_path):
    s = Store('demo', tmp_path / 'public.json', workspace='falkordb')
    proof = graph_showcase(s)
    assert proof['backend'] == 'demo'
    assert proof['native_cypher_executed'] is False
    assert proof['entity_count'] == 332
    assert proof['relationship_count'] == 378
    assert len(proof['paths']) == 3
    assert all(p['relationships'] == ['OWNS', 'VERSION'] for p in proof['paths'])
    assert all(p['nodes'][1]['name'] == 'FalkorDB/falkordb-py' for p in proof['paths'])
    assert all(p['nodes'][2]['source_url'].startswith('https://github.com/') for p in proof['paths'])
    assert proof['cypher'] == CYPHER
    assert proof['parameters']['repo'] == 'repo_720742399'


def test_showcase_api_rejects_other_workspace_and_untrusted_parameters(tmp_path):
    s = Store('demo', tmp_path / 'public.json', workspace='falkordb')
    with TestClient(app) as client:
        app.state.public_store = s
        assert client.get('/api/graph/showcase?workspace=novapay').status_code == 422
        result = client.get('/api/graph/showcase?workspace=falkordb&query=MATCH%20(n)%20DETACH%20DELETE%20n')
        assert result.status_code == 200
        assert result.json()['native_cypher_executed'] is False
        assert result.json()['cypher'] == CYPHER
        assert s.get('org_falkordb') is not None
