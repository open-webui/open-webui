from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.routers import openai as openai_router


def build_request(*, cookies: dict, oauth_token: dict | None):
    oauth_manager = SimpleNamespace(get_oauth_token=AsyncMock(return_value=oauth_token))
    request = SimpleNamespace(
        cookies=cookies,
        state=SimpleNamespace(
            token=HTTPAuthorizationCredentials(scheme='Bearer', credentials='session-token')
        ),
        app=SimpleNamespace(state=SimpleNamespace(oauth_manager=oauth_manager)),
    )
    return request, oauth_manager


class TestOpenAIHeadersAndCookies:
    @pytest.mark.asyncio
    async def test_system_oauth_refreshes_forwarded_oauth_id_token(self):
        request, oauth_manager = build_request(
            cookies={
                'oauth_session_id': 'session-1',
                'oauth_id_token': 'stale-id-token',
                'other_cookie': 'keep-me',
            },
            oauth_token={
                'access_token': 'fresh-access-token',
                'id_token': 'fresh-id-token',
            },
        )

        headers, cookies = await openai_router.get_headers_and_cookies(
            request,
            'https://example.com',
            config={'auth_type': 'system_oauth'},
            user=SimpleNamespace(id='user-1'),
        )

        oauth_manager.get_oauth_token.assert_awaited_once_with('user-1', 'session-1')
        assert headers['Authorization'] == 'Bearer fresh-access-token'
        assert cookies['oauth_id_token'] == 'fresh-id-token'
        assert cookies['other_cookie'] == 'keep-me'

    @pytest.mark.asyncio
    async def test_system_oauth_keeps_existing_cookie_when_refreshed_token_has_no_id_token(self):
        request, oauth_manager = build_request(
            cookies={
                'oauth_session_id': 'session-1',
                'oauth_id_token': 'existing-id-token',
            },
            oauth_token={
                'access_token': 'fresh-access-token',
            },
        )

        headers, cookies = await openai_router.get_headers_and_cookies(
            request,
            'https://example.com',
            config={'auth_type': 'system_oauth'},
            user=SimpleNamespace(id='user-1'),
        )

        oauth_manager.get_oauth_token.assert_awaited_once_with('user-1', 'session-1')
        assert headers['Authorization'] == 'Bearer fresh-access-token'
        assert cookies['oauth_id_token'] == 'existing-id-token'
