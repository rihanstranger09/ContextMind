"""FalkorDB connection settings. Secrets are read at runtime, never stored in Git."""
import os
from app import config  # load ignored .env before reading connection settings
from urllib.parse import unquote, urlsplit


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

    if not host or not 1 <= port <= 65535:
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
