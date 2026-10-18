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
    (socket.gaierror('Name or service not known'), 'unreachable'),
    (ConnectionRefusedError('refused'), 'unreachable'),
    (ResponseError('unknown command'), 'server_error'),
    (RuntimeError('surprise at db.invalid'), 'unknown'),
])
def test_classify_graph_error(error, expected):
    category = classify_graph_error(error)
    assert category == expected
    # Hints are static operator guidance; they can never contain an endpoint.
    assert 'db.invalid' not in GRAPH_ERROR_HINTS[category]
