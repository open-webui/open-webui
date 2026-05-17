"""
Lightweight helpers for OAuth session selection.

Kept in a separate module so they can be unit-tested without importing
the full middleware chain.
"""


def select_sso_session(sessions):
    """Return the most-recent non-MCP OAuth session, or None.

    MCP sessions (provider starting with 'mcp:') are excluded because they
    must be refreshed via oauth_client_manager, not the SSO oauth_manager.
    Passing them to the SSO manager causes it to fail the refresh and delete
    the session (see #24618).
    """
    sso_sessions = [s for s in sessions if not (s.provider or '').startswith('mcp:')]
    if not sso_sessions:
        return None
    return max(sso_sessions, key=lambda s: s.updated_at)
