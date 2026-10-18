"""Cloud configuration never needs a live account in the normal test suite."""
from types import SimpleNamespace
import pytest
from graph.connection import connection_options
from graph.store import Store


@pytest.fixture(autouse=True)
def clear_connection_env(monkeypatch):
    for key in ('FALKOR_URL', 'FALKOR_HOST', 'FALKOR_PORT', 'FALKOR_USERNAME',
                'FALKOR_PASSWORD', 'FALKOR_SSL', 'FALKOR_CA_CERTS',
                'FALKORDB_HOST', 'FALKORDB_PORT', 'FALKORDB_USERNAME',
                'FALKORDB_PASSWORD', 'FALKORDB_SSL'):
        monkeypatch.delenv(key, raising=False)


def test_local_compose_defaults():
    config = connection_options()
    assert config['host'] == 'localhost'
    assert config['port'] == 6379
    assert config['ssl'] is False
    assert config['password'] is None
    assert 'ssl_cert_reqs' not in config


def test_cloud_individual_settings(monkeypatch):
    for key, value in dict(FALKOR_HOST='db.example.org', FALKOR_PORT='6380',
                           FALKOR_USERNAME='default', FALKOR_PASSWORD='p@ss word',
                           FALKOR_SSL='true', FALKOR_CA_CERTS='/tmp/ca.pem').items():
        monkeypatch.setenv(key, value)
    config = connection_options()
    assert config == dict(host='db.example.org', port=6380, username='default',
                          password='p@ss word', ssl=True, ssl_cert_reqs='required',
                          ssl_check_hostname=True, ssl_ca_certs='/tmp/ca.pem',
                          socket_timeout=10, socket_connect_timeout=5)


def test_cloud_url_decodes_credentials_and_enables_tls(monkeypatch):
    monkeypatch.setenv('FALKOR_URL', 'rediss://user%40org:p%40ss%3Aword@db.example.org:6380/0')
    config = connection_options()
    assert config['username'] == 'user@org'
    assert config['password'] == 'p@ss:word'
    assert config['host'] == 'db.example.org' and config['port'] == 6380
    assert config['ssl'] and config['ssl_check_hostname']
    assert config['ssl_cert_reqs'] == 'required'


@pytest.mark.parametrize('settings', [
    {'FALKOR_URL': 'https://user:secret@db.example.org'},
    {'FALKOR_URL': 'rediss://user:secret@db.example.org/1'},
    {'FALKOR_URL': 'rediss://user:secret@db.example.org:bad'},
    {'FALKOR_URL': 'rediss://user:secret@db.example.org', 'FALKOR_HOST': 'localhost'},
    {'FALKOR_SSL': 'maybe'},
    {'FALKOR_CA_CERTS': '/tmp/ca.pem'},
    {'FALKOR_PORT': '65536'},
])
def test_invalid_config_does_not_echo_secret(monkeypatch, settings):
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError) as exc:
        connection_options()
    assert 'secret' not in str(exc.value)


def test_store_passes_cloud_options_to_driver(monkeypatch):
    import falkordb
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(('connect', kwargs))

        def select_graph(self, name):
            calls.append(('graph', name))
            return self

        def query(self, query, params=None):
            return SimpleNamespace(result_set=[['org_falkordb']])

    monkeypatch.setattr(falkordb, 'FalkorDB', FakeClient)
    monkeypatch.setenv('FALKOR_URL', 'rediss://default:secret@db.example.org:6380')
    monkeypatch.setenv('FALKOR_GRAPH', 'test_cloud')
    s = Store('falkordb', workspace='falkordb')
    assert s.backend == 'falkordb'
    assert calls[0][1]['ssl'] and calls[0][1]['password'] == 'secret'
    assert calls[1] == ('graph', 'test_cloud_public_falkordb')
