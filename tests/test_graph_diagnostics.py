"""Health diagnostics classify connection failures without leaking endpoints."""
import socket
import ssl

import pytest
from redis.exceptions import (AuthenticationError, ConnectionError as RedisConnectionError,
                              ResponseError, TimeoutError as RedisTimeoutError)

from graph.connection import GRAPH_ERROR_HINTS, classify_graph_error


@pytest.mark.parametrize('error,expected', [
    (ValueError('Invalid FALKOR_PORT'), 'config_invalid'),
    (AuthenticationError('WRONGPASS invalid username-password pair'), 'auth_failed'),
    (ResponseError('NOAUTH Authentication required at db.invalid'), 'auth_failed'),
    (ssl.SSLError('handshake failure'), 'tls_failed'),
    (RedisTimeoutError('Timeout connecting to db.invalid'), 'timeout'),
    (RedisConnectionError('Error connecting to db.invalid'), 'unreachable'),
    (socket.gaierror('Name or service not known'), 'dns_failed'),
    (RedisConnectionError('Error -2 connecting to db.invalid. Name or service not known.'), 'dns_failed'),
    (ConnectionRefusedError('refused'), 'connection_refused'),
    (RedisConnectionError('Error 111 connecting to db.invalid. Connection refused.'), 'connection_refused'),
    (RedisConnectionError('Connection closed by server'), 'connection_closed'),
    (ConnectionResetError('reset'), 'connection_closed'),
    (ResponseError('unknown command'), 'server_error'),
    (RuntimeError('surprise at db.invalid'), 'unknown'),
])
def test_classify_graph_error(error, expected):
    category = classify_graph_error(error)
    assert category == expected
    # Hints are static operator guidance; they can never contain an endpoint.
    assert 'db.invalid' not in GRAPH_ERROR_HINTS[category]


@pytest.mark.parametrize('host', ['https://db.example.org', 'db.example.org:6380/path', 'db example.org'])
def test_url_pasted_into_host_field_is_config_invalid(monkeypatch, host):
    from graph.connection import connection_options
    for key in ('FALKOR_URL', 'FALKOR_HOST', 'FALKOR_PORT', 'FALKOR_USERNAME', 'FALKOR_PASSWORD',
                'FALKOR_SSL', 'FALKOR_CA_CERTS', 'FALKORDB_PORT', 'FALKORDB_USERNAME',
                'FALKORDB_PASSWORD', 'FALKORDB_SSL'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('FALKORDB_HOST', host)
    with pytest.raises(ValueError, match='Invalid FalkorDB host'):
        connection_options()
    monkeypatch.setenv('FALKORDB_HOST', '  db.example.org  ')
    assert connection_options()['host'] == 'db.example.org'
