"""Health diagnostics classify connection failures without leaking endpoints."""
import socket
import ssl

import pytest
from redis.exceptions import (AuthenticationError, ConnectionError as RedisConnectionError,
                              ResponseError, TimeoutError as RedisTimeoutError)

from graph.connection import GRAPH_ERROR_HINTS, classify_graph_error, graph_error_errno


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


def test_lambda_ebusy_getaddrinfo_failure_is_dns_failed():
    # Vercel/Lambda-style runtimes surface DNS failure as OSError Errno 16.
    try:
        try:
            raise OSError(16, 'Device or resource busy')
        except OSError as inner:
            raise RedisConnectionError('Error connecting to db.invalid') from inner
    except RedisConnectionError as wrapped:
        assert classify_graph_error(wrapped) == 'dns_failed'
        assert graph_error_errno(wrapped) == 16


def test_wrapped_socket_errors_classify_through_the_chain():
    try:
        try:
            raise OSError(101, 'Network is unreachable')
        except OSError as inner:
            raise RedisConnectionError('Error connecting to db.invalid') from inner
    except RedisConnectionError as wrapped:
        assert classify_graph_error(wrapped) == 'network_unreachable'
        assert graph_error_errno(wrapped) == 101
    try:
        try:
            raise ConnectionRefusedError(111, 'Connection refused')
        except ConnectionRefusedError as inner:
            raise RedisConnectionError('Error connecting to db.invalid') from inner
    except RedisConnectionError as wrapped:
        assert classify_graph_error(wrapped) == 'connection_refused'
        assert graph_error_errno(wrapped) == 111
    assert graph_error_errno(RuntimeError('no errno here')) is None


@pytest.mark.parametrize('host', ['https://db.example.org', 'db.example.org:6380/path', 'db example.org', 'db.example.org:6380'])
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
