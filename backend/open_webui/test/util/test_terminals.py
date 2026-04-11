from open_webui.utils.terminals import build_terminal_ws_url


def test_build_terminal_ws_url_adds_bearer_token_query_param():
    url = build_terminal_ws_url(
        base_url='http://orchestrator.openwebui.svc.cluster.local:8080/',
        session_id='abc123',
        user_id='user-1',
        auth_type='bearer',
        key='secret-token',
    )

    assert (
        url
        == 'ws://orchestrator.openwebui.svc.cluster.local:8080/api/terminals/abc123?user_id=user-1&token=secret-token'
    )


def test_build_terminal_ws_url_uses_policy_route_when_configured():
    url = build_terminal_ws_url(
        base_url='https://orchestrator.example.com',
        session_id='abc123',
        user_id='user-1',
        policy_id='policy-9',
        auth_type='bearer',
        key='secret-token',
    )

    assert (
        url
        == 'wss://orchestrator.example.com/p/policy-9/api/terminals/abc123?user_id=user-1&token=secret-token'
    )


def test_build_terminal_ws_url_omits_token_for_non_bearer_auth():
    url = build_terminal_ws_url(
        base_url='https://orchestrator.example.com',
        session_id='abc123',
        user_id='user-1',
        auth_type='session',
        key='secret-token',
    )

    assert url == 'wss://orchestrator.example.com/api/terminals/abc123?user_id=user-1'
