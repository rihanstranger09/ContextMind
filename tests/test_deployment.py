"""Vercel deployment contract: config, hosted-DB aliases, fail-closed health,
and the offline logic of the deployment verifier. No network or secrets."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        'verify_deployment', ROOT / 'scripts/verify_deployment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vercel_config_targets_fastapi_entrypoint_and_bundles_assets():
    config = json.loads((ROOT / 'vercel.json').read_text())
    function = config['functions']['app/main.py']
    assert function['maxDuration'] >= 60
    for needed in ('frontend/**', 'data/sample_company.json', 'data/falkordb/snapshot.json'):
        assert needed in function['includeFiles']
    assert 'presentation/**' in function['excludeFiles']
    assert (ROOT / '.python-version').read_text().strip() == '3.12'
    ignore = (ROOT / '.vercelignore').read_text()
    assert '.env' in ignore and 'presentation/*.mp4' in ignore


def test_fastapi_app_is_importable_without_a_graph_connection():
    # Vercel's FastAPI preset imports `app` from app/main.py; importing must
    # never open a database connection (stores are built lazily).
    from app.main import app
    paths = {route.path for route in app.routes}
    assert {'/api/health', '/api/graph/showcase', '/api/graph/company-proof', '/dashboard'} <= paths


@pytest.fixture
def clear_connection_env(monkeypatch):
    for key in ('FALKOR_URL', 'FALKOR_HOST', 'FALKOR_PORT', 'FALKOR_USERNAME',
                'FALKOR_PASSWORD', 'FALKOR_SSL', 'FALKOR_CA_CERTS',
                'FALKORDB_HOST', 'FALKORDB_PORT', 'FALKORDB_USERNAME',
                'FALKORDB_PASSWORD', 'FALKORDB_SSL'):
        monkeypatch.delenv(key, raising=False)


def test_hosted_dashboard_aliases_are_accepted(clear_connection_env, monkeypatch):
    from graph.connection import connection_options
    for key, value in dict(FALKORDB_HOST='db.example.org', FALKORDB_PORT='6380',
                           FALKORDB_USERNAME='falkordb', FALKORDB_PASSWORD='p@ss',
                           FALKORDB_SSL='true').items():
        monkeypatch.setenv(key, value)
    config = connection_options()
    assert config['host'] == 'db.example.org' and config['port'] == 6380
    assert config['username'] == 'falkordb' and config['password'] == 'p@ss'
    assert config['ssl'] and config['ssl_cert_reqs'] == 'required'


def test_blank_dashboard_values_count_as_unset(clear_connection_env, monkeypatch):
    from graph.connection import connection_options
    for key in ('FALKORDB_HOST', 'FALKORDB_PORT', 'FALKORDB_PASSWORD'):
        monkeypatch.setenv(key, '')
    config = connection_options()
    assert config['host'] == 'localhost' and config['port'] == 6379 and config['password'] is None
    # A rediss URL alongside only-blank individual keys is not a conflict.
    monkeypatch.setenv('FALKOR_URL', 'rediss://default:secret@db.example.org:6380')
    assert connection_options()['host'] == 'db.example.org'
    # A non-blank alias still conflicts with FALKOR_URL.
    monkeypatch.setenv('FALKORDB_USERNAME', 'falkordb')
    with pytest.raises(ValueError, match='cannot be combined'):
        connection_options()


def test_unreachable_graph_fails_closed_but_pages_still_serve(monkeypatch):
    import app.main as main
    from fastapi.testclient import TestClient

    class BrokenStore:
        def __init__(self, *args, **kwargs):
            raise OSError('simulated unreachable hosted graph at db.invalid:6380')

    monkeypatch.setattr(main, 'Store', BrokenStore)
    monkeypatch.setenv('GRAPH_BACKEND', 'falkordb')
    saved = {attr: getattr(main.app.state, attr, None) for attr in ('store', 'public_store')}
    for attr in saved:
        if hasattr(main.app.state, attr):
            delattr(main.app.state, attr)
    main._STORE_FAILURES.clear()
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            health = client.get('/api/health')
            assert health.status_code == 503
            body = health.json()
            assert body['status'] == 'unhealthy' and body['graph_ready'] is False
            assert body['graph_mode'] == 'unavailable' and body['graph_configured'] == 'falkordb'
            assert 'db.invalid' not in health.text  # endpoint details never reflected
            assert client.get('/api/entities').status_code == 503
            assert client.get('/dashboard').status_code == 200
    finally:
        main._STORE_FAILURES.clear()
        for attr, value in saved.items():
            if value is not None:
                setattr(main.app.state, attr, value)
            elif hasattr(main.app.state, attr):
                delattr(main.app.state, attr)


GOOD_HEALTH = {'status': 'healthy', 'graph_mode': 'falkordb', 'graph_ready': True}
GOOD_COMPANY = {'native_cypher_executed': True, 'backend': 'falkordb', 'evidence': [{}] * 4}
GOOD_PUBLIC = {'native_cypher_executed': True, 'backend': 'falkordb',
               'entity_count': 332, 'relationship_count': 378, 'paths': [{}] * 3}


def _stub(health=GOOD_HEALTH, company=GOOD_COMPANY, public=GOOD_PUBLIC, http=200):
    def get_json(url):
        if '/api/health?workspace=novapay' in url:
            return http, dict(health, workspace='novapay')
        if '/api/health?workspace=falkordb' in url:
            return http, dict(health, workspace='falkordb')
        if 'company-proof' in url:
            return http, company
        return http, public
    return get_json, lambda url: (200, '<title>ContextMind</title>')


def test_verifier_passes_only_a_fully_native_deployment():
    verifier = load_verifier()
    results = verifier.run_checks('https://example.test', *_stub())
    assert len(results) == 5 and all(ok for _, ok, _ in results)


@pytest.mark.parametrize('override', [
    dict(health={'status': 'healthy', 'graph_mode': 'demo', 'graph_ready': True}),
    dict(health={'status': 'unhealthy', 'graph_mode': 'unavailable', 'graph_ready': False}, http=503),
    dict(company=dict(GOOD_COMPANY, native_cypher_executed=False, backend='demo')),
    dict(public=dict(GOOD_PUBLIC, entity_count=12)),
    dict(company=dict(GOOD_COMPANY, evidence=[{}])),
])
def test_verifier_fails_closed(override):
    verifier = load_verifier()
    results = verifier.run_checks('https://example.test', *_stub(**override))
    assert not all(ok for _, ok, _ in results)
