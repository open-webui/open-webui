from types import SimpleNamespace

from open_webui.utils.terminals import build_terminal_proxy_auth, build_terminal_ws_url


def _request(headers=None, cookies=None, token=None):
    return SimpleNamespace(
        headers=headers or {},
        cookies=cookies or {},
        state=SimpleNamespace(token=token),
    )


def test_build_terminal_proxy_auth_bearer():
    headers, cookies, auth_type = build_terminal_proxy_auth(
        _request(),
        {'auth_type': 'bearer', 'key': 'secret-token'},
        'user-1',
    )

    assert auth_type == 'bearer'
    assert headers == {
        'X-User-Id': 'user-1',
        'Authorization': 'Bearer secret-token',
    }
    assert cookies == {}


def test_build_terminal_proxy_auth_session():
    request = _request(
        headers={'x-session-id': 'session-1'},
        cookies={'token': 'cookie-token'},
        token=SimpleNamespace(credentials='session-token'),
    )

    headers, cookies, auth_type = build_terminal_proxy_auth(
        request,
        {'auth_type': 'session'},
        'user-1',
    )

    assert auth_type == 'session'
    assert headers == {
        'X-User-Id': 'user-1',
        'X-Session-Id': 'session-1',
        'Authorization': 'Bearer session-token',
    }
    assert cookies == {'token': 'cookie-token'}


def test_build_terminal_proxy_auth_system_oauth():
    request = _request(
        headers={'x-oauth-access-token': 'oauth-token'},
        cookies={'oauth': 'cookie'},
    )

    headers, cookies, auth_type = build_terminal_proxy_auth(
        request,
        {'auth_type': 'system_oauth'},
        'user-1',
    )

    assert auth_type == 'system_oauth'
    assert headers == {
        'X-User-Id': 'user-1',
        'Authorization': 'Bearer oauth-token',
    }
    assert cookies == {'oauth': 'cookie'}


def test_build_terminal_proxy_auth_session_uses_explicit_session_token():
    request = _request(
        headers={'x-session-id': 'session-1'},
        cookies={'token': 'cookie-token'},
        token=None,
    )

    headers, cookies, auth_type = build_terminal_proxy_auth(
        request,
        {'auth_type': 'session'},
        'user-1',
        session_token='validated-jwt',
    )

    assert auth_type == 'session'
    assert headers == {
        'X-User-Id': 'user-1',
        'X-Session-Id': 'session-1',
        'Authorization': 'Bearer validated-jwt',
    }
    assert cookies == {'token': 'cookie-token'}


def test_build_terminal_ws_url_uses_policy_route_when_configured():
    url = build_terminal_ws_url(
        base_url='https://orchestrator.example.com',
        session_id='abc123',
        user_id='user-1',
        policy_id='policy-9',
    )

    assert url == 'wss://orchestrator.example.com/p/policy-9/api/terminals/abc123?user_id=user-1'
