from urllib.parse import urlencode


def build_terminal_ws_url(
    base_url: str,
    session_id: str,
    user_id: str,
    *,
    policy_id: str | None = None,
    auth_type: str = 'bearer',
    key: str = '',
) -> str:
    ws_base = base_url.rstrip('/').replace('https://', 'wss://').replace('http://', 'ws://')

    if policy_id:
        upstream_url = f'{ws_base}/p/{policy_id}/api/terminals/{session_id}'
    else:
        upstream_url = f'{ws_base}/api/terminals/{session_id}'

    upstream_params = {'user_id': user_id}
    if auth_type == 'bearer' and key:
        upstream_params['token'] = key

    return f'{upstream_url}?{urlencode(upstream_params)}'
