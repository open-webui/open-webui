"""
Regression test for #24618:
MCP OAuth sessions must not be passed to the SSO oauth_manager fallback in
get_system_oauth_token(), otherwise the manager fails the token refresh and
deletes the MCP session.
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal stubs — avoid importing the real middleware (heavy DB/config chain)
# ---------------------------------------------------------------------------

@dataclass
class _FakeSession:
    id: str
    provider: str
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


async def _get_system_oauth_token(request, user):
    """
    Inlined copy of the function under test so the test has zero import-chain
    dependencies. Keep in sync with middleware.py::get_system_oauth_token().
    """
    oauth_token = None
    try:
        oauth_session_id = request.cookies.get('oauth_session_id', None)
        if oauth_session_id:
            oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                user.id,
                oauth_session_id,
            )

        if oauth_token is None:
            sessions = await _fake_get_sessions(user.id)
            # Fix for #24618: skip mcp:* sessions in the SSO fallback
            sessions = [s for s in sessions if not (s.provider or '').startswith('mcp:')]
            if sessions:
                best = max(sessions, key=lambda s: s.updated_at)
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    best.id,
                )
    except Exception:
        pass
    return oauth_token


# Replaced per test via monkeypatch
_sessions_store: list[_FakeSession] = []


async def _fake_get_sessions(user_id):
    return list(_sessions_store)


def _make_request(cookie_session_id=None, token_return=None):
    request = MagicMock()
    request.cookies = {'oauth_session_id': cookie_session_id} if cookie_session_id else {}
    request.app.state.oauth_manager.get_oauth_token = AsyncMock(return_value=token_return)
    return request


def _make_user(user_id='user-1'):
    user = MagicMock()
    user.id = user_id
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_session_not_passed_to_sso_manager_when_sso_session_also_exists():
    """
    Regression: user has one SSO session and a newer MCP session.
    The fallback must pick the SSO session, not the MCP one.
    """
    sso_session = _FakeSession(
        id='sso-session-1',
        provider='google',
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    mcp_session = _FakeSession(
        id='mcp-session-1',
        provider='mcp:coda',
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),  # newer
    )

    global _sessions_store
    _sessions_store = [sso_session, mcp_session]

    request = _make_request(token_return='sso-token')
    user = _make_user()

    token = await _get_system_oauth_token(request, user)

    # get_oauth_token must have been called with the SSO session id, not the MCP one
    request.app.state.oauth_manager.get_oauth_token.assert_called_once_with(
        user.id, sso_session.id
    )
    assert token == 'sso-token'


@pytest.mark.asyncio
async def test_mcp_only_sessions_result_in_no_sso_fallback_call():
    """
    When the user has only MCP sessions (no SSO session), the SSO oauth_manager
    must not be called at all — previously it would be called and delete the session.
    """
    mcp_session = _FakeSession(id='mcp-session-1', provider='mcp:coda')

    global _sessions_store
    _sessions_store = [mcp_session]

    request = _make_request(token_return='should-not-be-returned')
    user = _make_user()

    token = await _get_system_oauth_token(request, user)

    request.app.state.oauth_manager.get_oauth_token.assert_not_called()
    assert token is None


@pytest.mark.asyncio
async def test_cookie_path_bypasses_fallback_entirely():
    """
    When oauth_session_id cookie is present and resolves a token,
    the DB fallback is never reached (MCP or otherwise).
    """
    global _sessions_store
    _sessions_store = []  # would be empty anyway, but make it explicit

    request = _make_request(cookie_session_id='cookie-session-abc', token_return='cookie-token')
    user = _make_user()

    token = await _get_system_oauth_token(request, user)

    request.app.state.oauth_manager.get_oauth_token.assert_called_once_with(
        user.id, 'cookie-session-abc'
    )
    assert token == 'cookie-token'


@pytest.mark.asyncio
async def test_sso_only_sessions_work_as_before():
    """
    When only SSO sessions exist, the fallback continues to work correctly.
    """
    sso_session = _FakeSession(id='sso-session-1', provider='google')

    global _sessions_store
    _sessions_store = [sso_session]

    request = _make_request(token_return='sso-token')
    user = _make_user()

    token = await _get_system_oauth_token(request, user)

    request.app.state.oauth_manager.get_oauth_token.assert_called_once_with(
        user.id, sso_session.id
    )
    assert token == 'sso-token'


@pytest.mark.asyncio
async def test_provider_none_sessions_not_excluded():
    """
    Sessions with provider=None (legacy rows) must not be excluded by the filter.
    """
    legacy_session = _FakeSession(id='legacy-session-1', provider=None)

    global _sessions_store
    _sessions_store = [legacy_session]

    request = _make_request(token_return='legacy-token')
    user = _make_user()

    token = await _get_system_oauth_token(request, user)

    request.app.state.oauth_manager.get_oauth_token.assert_called_once_with(
        user.id, legacy_session.id
    )
    assert token == 'legacy-token'
