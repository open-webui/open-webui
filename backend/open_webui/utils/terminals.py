from urllib.parse import urlencode


def build_terminal_proxy_auth(request, connection: dict, user_id: str) -> tuple[dict, dict, str]:
    headers = {'X-User-Id': user_id}

    session_id = request.headers.get('x-session-id')
    if session_id:
        headers['X-Session-Id'] = session_id

    cookies = {}
    auth_type = connection.get('auth_type', 'bearer')

    if auth_type == 'bearer':
        headers['Authorization'] = f'Bearer {connection.get("key", "")}'
    elif auth_type == 'session':
        cookies = request.cookies
        token = getattr(getattr(request.state, 'token', None), 'credentials', None)
        if token:
            headers['Authorization'] = f'Bearer {token}'
    elif auth_type == 'system_oauth':
        cookies = request.cookies
        oauth_token = request.headers.get('x-oauth-access-token', '')
        if oauth_token:
            headers['Authorization'] = f'Bearer {oauth_token}'

    return headers, cookies, auth_type


def build_terminal_ws_url(
    base_url: str,
    session_id: str,
    user_id: str,
    *,
    policy_id: str | None = None,
) -> str:
    ws_base = base_url.rstrip('/').replace('https://', 'wss://').replace('http://', 'ws://')

    if policy_id:
        upstream_url = f'{ws_base}/p/{policy_id}/api/terminals/{session_id}'
    else:
        upstream_url = f'{ws_base}/api/terminals/{session_id}'

    return f'{upstream_url}?{urlencode({"user_id": user_id})}'
