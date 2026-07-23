"""Shared routing helpers for admin-configured terminal servers."""

from urllib.parse import quote


def get_terminal_server_url(connection: dict) -> str:
    """Return the upstream base URL for a terminal connection.

    An explicit policy uses the named-policy route. Connections without one
    keep their existing root route.
    """
    base_url = str(connection.get('url') or '').rstrip('/')
    policy_id = str(connection.get('policy_id') or '').strip()
    if policy_id:
        return f'{base_url}/p/{quote(policy_id, safe="")}'
    return base_url
