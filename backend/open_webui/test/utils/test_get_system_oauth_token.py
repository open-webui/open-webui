"""
Regression test for #24618:
MCP OAuth sessions must not be passed to the SSO oauth_manager fallback in
get_system_oauth_token(), otherwise the manager fails the token refresh and
deletes the MCP session.

Tests the select_sso_session() helper extracted from middleware.py so that
the suite exercises the real production function rather than an inlined copy.
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from open_webui.utils.oauth_session_utils import select_sso_session


# Minimal session stub


@dataclass
class _FakeSession:
    id: str
    provider: str | None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Tests for select_sso_session()


def test_mcp_session_not_passed_to_sso_manager_when_sso_session_also_exists():
    """
    Regression: user has one SSO session and a newer MCP session.
    The helper must return the SSO session, not the MCP one.
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

    result = select_sso_session([sso_session, mcp_session])

    assert result is sso_session


def test_mcp_only_sessions_result_in_no_sso_fallback_call():
    """
    When the user has only MCP sessions (no SSO session), the helper must
    return None so the SSO oauth_manager is never invoked — preventing the
    session from being deleted.
    """
    mcp_session = _FakeSession(id='mcp-session-1', provider='mcp:coda')

    result = select_sso_session([mcp_session])

    assert result is None


def test_empty_sessions_returns_none():
    """No sessions at all → None."""
    assert select_sso_session([]) is None


def test_sso_only_sessions_work_as_before():
    """
    When only SSO sessions exist, the helper returns the most recent one.
    Ensures no regression for users without MCP.
    """
    older = _FakeSession(
        id='sso-old',
        provider='google',
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = _FakeSession(
        id='sso-new',
        provider='microsoft',
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    result = select_sso_session([older, newer])

    assert result is newer


def test_provider_none_sessions_not_excluded():
    """
    Sessions with provider=None (legacy rows) must not be excluded by the
    filter — the (s.provider or '') guard handles None safely.
    """
    legacy_session = _FakeSession(id='legacy-session-1', provider=None)

    result = select_sso_session([legacy_session])

    assert result is legacy_session


def test_multiple_mcp_prefixes_all_excluded():
    """
    Any provider starting with 'mcp:' must be excluded regardless of
    what follows the prefix.
    """
    sessions = [
        _FakeSession(id='a', provider='mcp:coda'),
        _FakeSession(id='b', provider='mcp:teams'),
        _FakeSession(id='c', provider='mcp:github'),
    ]

    result = select_sso_session(sessions)

    assert result is None
