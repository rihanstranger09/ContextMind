"""Cohere joins OpenAI as a live provider via the OpenAI-compatibility API.

No network and no real key: the SDK client class is replaced with the same
fake loop used by the OpenAI tests, and client construction is inspected.
"""
import pytest
from fastapi.testclient import TestClient

from agents.llm_agent import COHERE_BASE_URL, LiveAgent, create_client
from app.config import llm_config
from app.main import app
from graph.store import Store
from tests.test_live_agent import FakeLLM, message


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    for key in ('MODEL_NAME', 'OPENAI_API_KEY', 'COHERE_API_KEY'):
        monkeypatch.delenv(key, raising=False)


def test_cohere_config_uses_its_own_key_and_default_model(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'cohere')
    monkeypatch.setenv('COHERE_API_KEY', 'test-only-not-a-real-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-be-used')
    cfg = llm_config()
    assert cfg == {'provider': 'cohere', 'model': 'command-a-03-2025',
                   'api_key': 'test-only-not-a-real-key', 'api_key_env': 'COHERE_API_KEY'}
    monkeypatch.setenv('MODEL_NAME', 'command-r-plus-08-2024')
    assert llm_config()['model'] == 'command-r-plus-08-2024'
    monkeypatch.setenv('LLM_PROVIDER', 'bogus')
    with pytest.raises(ValueError, match='cohere'):
        llm_config()


def test_create_client_points_cohere_at_compatibility_endpoint(monkeypatch):
    seen = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr('openai.OpenAI', FakeOpenAI)
    create_client('cohere', 'test-only')
    assert seen == {'api_key': 'test-only', 'base_url': COHERE_BASE_URL, 'max_retries': 1}
    seen.clear()
    create_client('openai', 'test-only')
    assert seen == {'api_key': 'test-only', 'max_retries': 1}  # no base_url override
    with pytest.raises(ValueError):
        create_client('disabled', 'test-only')


def test_cohere_agent_mode_and_citations_match_openai_contract(tmp_path):
    graph = Store('demo', tmp_path / 'cohere-test.json')
    fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                   message(content='Platform Engineering is the recorded owner [E1].'))
    result = LiveAgent(graph, fake, model='command-a-03-2025', provider='cohere').ask('Who owns it?')
    assert result['agent_mode'] == 'cohere_tool_calling'
    assert result['model'] == 'command-a-03-2025'
    assert result['graph_trace'][0]['citation'] == 'E1'


def test_chat_endpoint_cohere_requires_native_graph_then_key(tmp_path, monkeypatch):
    graph = Store('demo', tmp_path / 'cohere-api.json')
    monkeypatch.setenv('LLM_PROVIDER', 'cohere')

    class NativeStub:
        # Route sees backend='falkordb'; every read delegates to the demo store.
        backend = 'falkordb'
        workspace = 'novapay'

        def __getattr__(self, name):
            return getattr(graph, name)

    with TestClient(app) as client:
        app.state.store = graph
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 503 and 'native' in r.json()['detail']
        app.state.store = NativeStub()
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 503 and 'COHERE_API_KEY' in r.json()['detail']
        assert client.get('/api/health').json()['synthesis'] == 'cohere_tool_calling'
        monkeypatch.setenv('COHERE_API_KEY', 'test-only-not-a-real-key')
        seen = {}
        fake = FakeLLM(message(calls=[('find_owner', {'system_or_project': 'Database Cluster'})]),
                       message(content='Platform Engineering is the recorded owner [E1].'))

        def fake_openai(**kwargs):
            seen.update(kwargs)
            return fake

        monkeypatch.setattr('openai.OpenAI', fake_openai)
        r = client.post('/api/chat', json={'question': 'Who owns Database Cluster?'})
        assert r.status_code == 200 and r.json()['agent_mode'] == 'cohere_tool_calling'
        assert seen['base_url'] == COHERE_BASE_URL
        assert client.get('/api/health').json()['llm_configured'] is True
