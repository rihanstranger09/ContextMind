"""Provider-free tests of the actual tool-call loop and native query adapter."""
import json
from types import SimpleNamespace as NS
import pytest
from fastapi.testclient import TestClient
from agents.llm_agent import LiveAgent, ABSTAIN, ABSTAIN_UNCITED, TOOLS
from app.main import app
from graph.store import Store


def message(content=None, calls=None):
    calls = [NS(id=f'call_{i}', function=NS(name=n, arguments=json.dumps(a)))
             for i, (n, a) in enumerate(calls or [])]
    return NS(content=content, tool_calls=calls,
              model_dump=lambda **kw: {'role': 'assistant', 'content': content,
                                         'tool_calls': [{'id': c.id, 'type': 'function',
                                         'function': {'name': c.function.name,
                                         'arguments': c.function.arguments}} for c in calls]})


class FakeLLM:
    def __init__(self, *messages):
        self.messages = list(messages)
        self.inputs = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.inputs.append(kwargs)
        return NS(choices=[NS(message=self.messages.pop(0))])


@pytest.fixture
def graph(tmp_path):
    return Store('demo', tmp_path / 'live-test.json')


@pytest.mark.parametrize('name,args,expected', [
    ('find_owner', {'system_or_project': 'Database Cluster'}, 'OWNS'),
    ('get_decision_provenance', {'decision_id': 'decision_delay'}, 'BASED_ON'),
    ('impact_analysis', {'target_system': 'Database Cluster', 'max_depth': 3}, 'DEPENDS_ON'),
    ('shortest_path', {'source_entity': 'Alice Johnson', 'target_entity': 'Database Cluster'}, 'WORKED_ON'),
])
def test_provider_selects_bounded_graph_tool_and_cites_actual_path(graph, name, args, expected):
    fake = FakeLLM(message(calls=[(name, args)]), message(content='Recorded relationship [E1].'))
    result = LiveAgent(graph, fake).ask('Which recorded relationship?')
    assert result['agent_mode'] == 'openai_tool_calling'
    assert result['answer'] == 'Recorded relationship [E1].'
    assert result['tool_steps'][0]['tool'] == name
    assert any(expected == e['type'] for p in result['graph_trace'] for e in p['edges'])
    assert json.loads(fake.inputs[1]['messages'][-1]['content'])['paths'][0]['citation'] == 'E1'
    assert fake.inputs[0]['tool_choice'] == 'required'
    assert graph.get(result['id'])['type'] == 'AgentDecision'


def test_absent_evidence_never_becomes_a_model_answer(graph):
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Lunar Colony'})]),
                   message(content='Alice owns it [E1].'))
    result = LiveAgent(graph, fake).ask('Who owns the Lunar Colony?')
    assert result['answer'] == ABSTAIN and not result['facts']
    assert result['tool_steps'][0]['results'] == 0
    # No evidence means no rewrite attempt either; the abstention stays factual.
    assert result['grounding'] == {'status': 'no_evidence', 'reason': None}
    assert len(fake.inputs) == 2


def test_invalid_and_hallucinated_tool_are_rejected(graph):
    agent = LiveAgent(graph, FakeLLM())
    assert agent.execute('run_cypher', '{"query":"MATCH (n) DELETE n"}')['error']
    assert agent.execute('impact_analysis', '{"target_system":"Database Cluster","max_depth":100}')['error']
    assert agent.execute('find_owner', '{"system_or_project":"Database Cluster","query":"DROP"}')['error']
    assert agent.execute('get_decision_provenance', '{"decision_id":"made_up"}')['paths'] == []
    assert len(TOOLS) == 4


def test_uncited_sentence_abstains_honestly(graph):
    draft = 'Recorded owner [E1]. Also the database is on fire.'
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                   message(content=draft),
                   message(content=draft))  # the bounded rewrite repeats the uncited claim
    result = LiveAgent(graph, fake).ask('Who owns it?')
    # Evidence existed, so the abstention must not claim otherwise.
    assert result['answer'] == ABSTAIN_UNCITED and not result['facts']
    assert result['grounding'] == {'status': 'rejected', 'reason': 'uncited_sentence'}
    assert 'tools' not in fake.inputs[2]  # rewrite is a plain completion, not a tool round
    assert graph.get(result['id'])['grounding']['status'] == 'rejected'


def test_bad_citation_is_not_trusted(graph):
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                   message(content='Made up claim [E999].'),
                   message(content='Still made up [E999].'))
    result = LiveAgent(graph, fake).ask('Who owns Database Cluster?')
    assert result['answer'] == ABSTAIN_UNCITED and not result['graph_trace']
    assert result['grounding'] == {'status': 'rejected', 'reason': 'unknown_citations'}


def test_rewrite_recovers_structural_but_cited_draft(graph):
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                   message(content='Here is the answer. Platform Engineering is the recorded owner [E1].'),
                   message(content='Platform Engineering is the recorded owner [E1].'))
    result = LiveAgent(graph, fake).ask('Who owns Database Cluster?')
    assert result['answer'] == 'Platform Engineering is the recorded owner [E1].'
    assert result['grounding'] == {'status': 'repaired', 'reason': 'uncited_sentence'}
    assert len(fake.inputs) == 3  # exactly one bounded rewrite was spent


def test_grouped_and_range_citations_normalized_but_still_validated(graph):
    fake = FakeLLM(message(calls=[('get_decision_provenance', {'decision_id': 'decision_delay'})]),
                   message(content='The decision rests on recorded sources [E1, E3]. '
                                   'The evidence set spans further records [E1-E5].'))
    result = LiveAgent(graph, fake).ask('Why was it delayed?')
    assert result['grounding'] == {'status': 'passed', 'reason': None}
    assert '[E1][E3]' in result['answer'] and '[E4]' in result['answer']
    assert len(fake.inputs) == 2  # normalization alone sufficed; no rewrite spent
    # A group smuggling an unknown ID still fails closed after expansion.
    fake = FakeLLM(message(calls=[('get_decision_provenance', {'decision_id': 'decision_delay'})]),
                   message(content='Supported claim [E1, E999].'),
                   message(content='Supported claim [E1, E999].'))
    result = LiveAgent(graph, fake).ask('Why was it delayed?')
    assert result['answer'] == ABSTAIN_UNCITED
    assert result['grounding']['reason'] == 'unknown_citations'


def test_no_api_key_fails_closed_not_deterministic(graph, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with TestClient(app) as client:
        app.state.store = graph
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 503
        assert 'native' in r.json()['detail']
        graph.backend = 'falkordb'
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 503 and 'OPENAI_API_KEY' in r.json()['detail']
        assert client.get('/api/health').json()['synthesis'] == 'openai_tool_calling'


def test_chat_endpoint_calls_model_in_native_mode(graph, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-not-a-real-key')
    class NativeStub:
        backend = 'falkordb'
        workspace = 'novapay'
        def __getattr__(self, name): return getattr(graph, name)
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                   message(content='Platform Engineering is the recorded owner [E1].'))
    monkeypatch.setattr('openai.OpenAI', lambda **kwargs: fake)
    with TestClient(app) as client:
        app.state.store = NativeStub()
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 200
        assert r.json()['agent_mode'] == 'openai_tool_calling'
        assert r.json()['graph_trace'][0]['citation'] == 'E1'


def test_native_store_uses_parameterized_graph_queries_with_fake_client(monkeypatch, graph):
    import falkordb
    queries = []
    class FakeDB:
        def select_graph(self, name):
            assert name == 'contextmind'
            return self
        def query(self, cypher, params=None):
            queries.append((cypher, params))
            if 'RETURN n.id LIMIT 1' in cypher: rows = [['sys_database']]
            elif 'RETURN n.payload LIMIT $limit' in cypher:
                rows = [[json.dumps(n)] for n in graph.search(type=(params or {}).get('kind') or None)]
            elif 'RETURN n.payload' in cypher:
                node = graph.get(params['id'])
                rows = [[json.dumps(node)]] if node else []
            elif 'RETURN a.id,type(r),b.id,r.payload' in cypher:
                rows = [[e['source'], e['type'], e['target'], json.dumps(e)]
                        for e in graph.adjacent(params['id'])]
            else: rows = []
            return NS(result_set=rows)
    monkeypatch.setattr(falkordb, 'FalkorDB', lambda **kw: FakeDB())
    native = Store('falkordb')
    result = LiveAgent(native, FakeLLM()).execute('shortest_path', json.dumps(
        {'source_entity': 'Alice Johnson', 'target_entity': 'Database Cluster'}))
    assert len(result['paths'][0]) == 2
    assert any('MATCH (a:Entity)-[r]->(b:Entity)' in q for q, _ in queries)
    assert any(p and p.get('id') == 'person_alice' for _, p in queries)


def test_db_aliases_and_one_command_seed(monkeypatch):
    from graph.connection import connection_options
    from backend import seed
    for key in ('FALKOR_URL', 'FALKOR_HOST', 'FALKOR_PORT', 'FALKOR_PASSWORD',
                'FALKOR_USERNAME', 'FALKOR_SSL'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('FALKORDB_HOST', 'localhost')
    monkeypatch.setenv('FALKORDB_PORT', '6380')
    monkeypatch.setenv('FALKORDB_PASSWORD', 'unit-only')
    conf = connection_options()
    assert (conf['host'], conf['port'], conf['password']) == ('localhost', 6380, 'unit-only')
    with pytest.raises(ValueError):
        monkeypatch.setenv('FALKOR_URL', 'redis://localhost:6379')
        connection_options()
    seen = []
    class FakeStore:
        def __init__(self, backend, workspace):
            assert backend == 'falkordb'
            seen.append(workspace)
            self.workspace = workspace
        def get(self, key):
            assert key == ('sys_database' if self.workspace == 'novapay' else 'org_falkordb')
            return {'id': key}
        def counts(self): return {'nodes': 1, 'relationships': 0}
    monkeypatch.setattr(seed, 'Store', FakeStore)
    seed.main()
    assert seen == ['novapay', 'falkordb']
