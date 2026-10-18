"""FalkorDB connection settings. Secrets are read at runtime, never stored in Git."""
import os
from app import config  # load ignored .env before reading connection settings
from urllib.parse import unquote, urlsplit

# Safe, credential-free diagnostics for /api/health. Driver error messages can
# embed hostnames, so only these coarse categories (and static hints) may
# ever leave the server.
GRAPH_ERROR_HINTS = {
    'config_invalid': 'Check variable formats: numeric port, plain hostname without https://, and no FALKOR_URL mixed with individual settings.',
    'auth_failed': 'The database rejected the credentials. Check the password variable, and add the provider-issued username variable if your instance has one.',
    'tls_failed': 'TLS handshake failed. Check whether the endpoint requires TLS (FALKORDB_SSL=true) or is plain Redis protocol.',
    'timeout': 'Connection timed out. The instance may be paused, or its host/port may be unreachable from the deployment region.',
    'dns_failed': 'The hostname does not resolve in public DNS (Lambda-style runtimes report this as Errno 16 EBUSY). In the provider console copy the EXTERNAL/public endpoint hostname only - not the internal endpoint, no https://, and put the port in its own variable. A quick local nslookup on the host should return a public IP.',
    'connection_refused': 'The host resolved but refused the connection. Check the port value and that the FalkorDB instance is running (not paused or stopped).',
    'connection_closed': 'The server closed the connection during setup. Usually a TLS mismatch (toggle FALKORDB_SSL) or the port is not the Redis-protocol port.',
    'network_unreachable': 'No network route to that host from Vercel. The value is likely the provider INTERNAL/private endpoint; copy the EXTERNAL/public Redis endpoint from the provider console instead, and check any IP allowlist.',
    'unreachable': 'Host could not be reached. Check host/port values, whether the endpoint requires TLS (FALKORDB_SSL=true), and that the instance is running and publicly reachable.',
    'server_error': 'The database answered with an error. Confirm this endpoint is a FalkorDB (graph module) instance.',
    'unknown': 'Unclassified connection failure. Re-check every connection variable against the provider console.',
}


def _error_chain(error):
    chain, seen, current = [], set(), error
    while current is not None and id(current) not in seen and len(chain) < 6:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return chain


def graph_error_errno(error):
    """First OS errno in the chain (a bare integer is safe to expose), else None."""
    for link in _error_chain(error):
        errno = getattr(link, 'errno', None)
        if isinstance(errno, int):
            return errno
    return None


# Our own static configuration messages. They never contain variable values,
# so /api/health may surface them verbatim as graph_error_detail.
SAFE_CONFIG_MESSAGES = {
    'FALKOR_URL cannot be combined with individual connection settings',
    'Invalid FALKOR_URL (use redis:// or rediss:// with database 0)',
    'Invalid FALKOR_PORT',
    'FALKOR_SSL must be true or false',
    'FalkorDB host is empty',
    'FalkorDB host must be a bare hostname (no scheme or path)',
    'FalkorDB host appears to include a port; put the port in its own variable',
    'FalkorDB host must not contain spaces',
    'Invalid FalkorDB host or port',
    'FALKOR_CA_CERTS requires TLS',
}


def graph_error_chain(error):
    """Exception class names in the chain (module.Name only; never messages)."""
    import re as _re
    names = []
    for link in _error_chain(error):
        label = _re.sub(r'[^A-Za-z0-9_.]', '', f'{type(link).__module__}.{type(link).__name__}')[:80]
        if label:
            names.append(label)
    return names


def classify_graph_error(error):
    """Map a config/driver exception to one safe category; never returns messages.

    Drivers wrap socket errors, so the whole __cause__/__context__ chain is
    inspected: class names, errno values, and token-wise message matches.
    """
    import socket as _socket
    chain = _error_chain(error)
    names = [type(link).__name__ for link in chain]
    modules = [type(link).__module__ or '' for link in chain]
    texts = [str(link).upper() for link in chain]
    errnos = [getattr(link, 'errno', None) for link in chain]

    def any_text(*tokens):
        return any(token in text for text in texts for token in tokens)

    if isinstance(error, ValueError):
        return 'config_invalid'
    if any(name.startswith('Authentication') for name in names) \
            or any_text('WRONGPASS', 'NOAUTH', 'INVALID USERNAME-PASSWORD', 'NO PASSWORD IS SET'):
        return 'auth_failed'
    if any(module.startswith('ssl') for module in modules) \
            or any('SSL' in name.upper() for name in names) or any_text('SSL', 'CERTIFICATE'):
        return 'tls_failed'
    if any(isinstance(link, TimeoutError) for link in chain) \
            or any(name in ('TimeoutError', 'ReadTimeout', 'ConnectTimeout') for name in names) \
            or 110 in errnos:
        return 'timeout'
    # Lambda-style sandboxes report getaddrinfo/DNS failure as OSError
    # Errno 16 (EBUSY) rather than gaierror - treat it as DNS on this path.
    if any(isinstance(link, _socket.gaierror) for link in chain) or 16 in errnos \
            or any_text('NAME OR SERVICE NOT KNOWN', 'NAME RESOLUTION', 'FAILED TO RESOLVE', 'NXDOMAIN'):
        return 'dns_failed'
    if any(isinstance(link, ConnectionRefusedError) for link in chain) \
            or 111 in errnos or any_text('CONNECTION REFUSED'):
        return 'connection_refused'
    if any(isinstance(link, (ConnectionResetError, BrokenPipeError, EOFError)) for link in chain) \
            or 104 in errnos or any_text('CONNECTION CLOSED', 'RESET BY PEER', 'EOF OCCURRED'):
        return 'connection_closed'
    if any(errno in (101, 113) for errno in errnos) \
            or any_text('NETWORK IS UNREACHABLE', 'NO ROUTE TO HOST', 'HOST IS DOWN'):
        return 'network_unreachable'
    if any(name in ('ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
                    'gaierror', 'NewConnectionError', 'BusyLoadingError') for name in names) \
            or any(isinstance(link, (ConnectionError, OSError)) for link in chain):
        return 'unreachable'
    if any(name in ('ResponseError', 'DataError') for name in names):
        return 'server_error'
    return 'unknown'


def connection_options():
    """Return FalkorDB client kwargs for a private instance or a TLS cloud endpoint.

    FALKOR_URL accepts a Redis URI because FalkorDB speaks the Redis protocol.
    We parse it rather than passing `url` to FalkorDB: that parameter is used by
    the driver's cluster discovery, not by its ordinary Redis connection.
    """
    url = os.getenv('FALKOR_URL')
    if url:
        # Blank values (for example keys pre-created empty in a hosting
        # dashboard) count as unset everywhere in this module.
        if any(os.getenv(key) for key in (
            'FALKOR_HOST', 'FALKOR_PORT', 'FALKOR_USERNAME', 'FALKOR_PASSWORD', 'FALKOR_SSL',
            'FALKORDB_HOST', 'FALKORDB_PORT', 'FALKORDB_USERNAME', 'FALKORDB_PASSWORD', 'FALKORDB_SSL'
        )):
            raise ValueError('FALKOR_URL cannot be combined with individual connection settings')
        try:
            parts = urlsplit(url)
            if parts.scheme not in ('redis', 'rediss') or not parts.hostname:
                raise ValueError()
            if parts.path not in ('', '/0') or parts.query or parts.fragment:
                raise ValueError()
            host, port = parts.hostname, parts.port or 6379
            username = unquote(parts.username) if parts.username is not None else None
            password = unquote(parts.password) if parts.password is not None else None
        except ValueError:
            # Do not put the URL in an exception: it may contain a password.
            raise ValueError('Invalid FALKOR_URL (use redis:// or rediss:// with database 0)') from None
        ssl = parts.scheme == 'rediss'
    else:
        # FALKORDB_* aliases match the variable names already used by the
        # hosted deployment dashboards; FALKOR_* keeps precedence.
        host = os.getenv('FALKOR_HOST') or os.getenv('FALKORDB_HOST') or 'localhost'
        try:
            port = int(os.getenv('FALKOR_PORT') or os.getenv('FALKORDB_PORT') or '6379')
        except ValueError:
            raise ValueError('Invalid FALKOR_PORT') from None
        username = os.getenv('FALKOR_USERNAME') or os.getenv('FALKORDB_USERNAME') or None
        password = os.getenv('FALKOR_PASSWORD') or os.getenv('FALKORDB_PASSWORD') or None
        flag = (os.getenv('FALKOR_SSL') or os.getenv('FALKORDB_SSL') or 'false').lower()
        if flag not in ('true', 'false'):
            raise ValueError('FALKOR_SSL must be true or false')
        ssl = flag == 'true'

    host = host.strip() if isinstance(host, str) else host
    username = (username.strip() or None) if isinstance(username, str) else username
    # Format mistakes get distinct, value-free messages (see SAFE_CONFIG_MESSAGES):
    # a URL/path in the host field, "host:port" pasted together (IPv6 has
    # several colons), or stray spaces are operator-fixable format errors.
    if not host:
        raise ValueError('FalkorDB host is empty')
    if '://' in host or '/' in host:
        raise ValueError('FalkorDB host must be a bare hostname (no scheme or path)')
    if host.count(':') == 1:
        raise ValueError('FalkorDB host appears to include a port; put the port in its own variable')
    if any(ch.isspace() for ch in host):
        raise ValueError('FalkorDB host must not contain spaces')
    if not 1 <= port <= 65535:
        raise ValueError('Invalid FalkorDB host or port')
    ca_certs = os.getenv('FALKOR_CA_CERTS') or None
    if ca_certs and not ssl:
        raise ValueError('FALKOR_CA_CERTS requires TLS')
    options = dict(host=host, port=port, username=username, password=password,
                   ssl=ssl, socket_timeout=10, socket_connect_timeout=5)
    if ssl:
        # Never silently disable certificate verification for cloud connections.
        options.update(ssl_cert_reqs='required', ssl_check_hostname=True)
        if ca_certs:
            options['ssl_ca_certs'] = ca_certs
    return options
