import asyncio
from types import SimpleNamespace

from open_webui.utils.tools import build_tool_server_headers


class EmptyOAuthClientManager:
    async def get_oauth_token(self, user_id, server_id):
        return {'access_token': ''}


def _request():
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(oauth_client_manager=EmptyOAuthClientManager())),
        cookies={},
        state=SimpleNamespace(token=SimpleNamespace(credentials='')),
    )


def _user():
    return SimpleNamespace(id='user-id', name='Test User', email='test@example.com', role='user')


def test_build_tool_server_headers_omits_empty_bearer_tokens():
    request = _request()
    user = _user()
    cases = [
        ({'auth_type': 'bearer', 'key': ''}, {}),
        ({'auth_type': 'session'}, {}),
        ({'auth_type': 'system_oauth'}, {'__oauth_token__': {'access_token': ''}}),
        ({'auth_type': 'oauth_2.1'}, {}),
    ]

    for connection, extra_params in cases:
        headers, _ = asyncio.run(
            build_tool_server_headers(
                connection,
                request,
                user,
                server_id='server-id',
                extra_params=extra_params,
            )
        )

        assert 'Authorization' not in headers
