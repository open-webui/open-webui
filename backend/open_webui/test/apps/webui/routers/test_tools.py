from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def build_request(server_connection=None):
    if server_connection is None:
        server_connection = {
            'type': 'mcp',
            'config': {'enable': True},
            'info': {'id': 'test-mcp'},
            'url': 'http://127.0.0.1:8765/mcp',
            'auth_type': 'none',
        }

    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(TOOL_SERVER_CONNECTIONS=[server_connection]),
                oauth_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(token=SimpleNamespace(credentials='token')),
        cookies={},
    )


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_returns_argument_metadata(monkeypatch):
    from open_webui.routers import tools as tools_router
    from open_webui.utils import middleware as middleware_module

    prompts_payload = [
        {
            'name': 'review_code',
            'title': 'Review Code',
            'description': 'Review source code',
            'arguments': [
                {
                    'name': 'code',
                    'description': 'Source snippet',
                    'required': True,
                },
                {
                    'name': 'language',
                    'description': 'Language name',
                    'required': False,
                },
            ],
        }
    ]

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            assert url == 'http://127.0.0.1:8765/mcp'
            assert headers in (None, {})
            yield self

        async def list_prompts(self):
            return prompts_payload

    monkeypatch.setattr(tools_router, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(tools_router, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = build_request()
    user = SimpleNamespace(id='user-1')

    response = await tools_router.get_mcp_prompt_list(request, 'test-mcp', user=user)
    parsed_response = tools_router.MCPPromptListResponse.model_validate(response)

    assert parsed_response.model_dump() == {
        'prompts': [
            {
                'name': 'review_code',
                'title': 'Review Code',
                'description': 'Review source code',
                'arguments': [
                    {
                        'name': 'code',
                        'description': 'Source snippet',
                        'required': True,
                    },
                    {
                        'name': 'language',
                        'description': 'Language name',
                        'required': False,
                    },
                ],
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_hides_taskgroup_error_details(monkeypatch):
    from open_webui.routers import tools as tools_router
    from open_webui.utils import middleware as middleware_module

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            if False:
                yield self
            raise ExceptionGroup(
                'unhandled errors in a TaskGroup',
                [RuntimeError('All connection attempts failed')],
            )

        async def list_prompts(self):
            raise AssertionError('Prompt list should not be requested after a failed connection.')

    monkeypatch.setattr(tools_router, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(tools_router, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = build_request()
    user = SimpleNamespace(id='user-1')

    with pytest.raises(tools_router.HTTPException) as exc_info:
        await tools_router.get_mcp_prompt_list(request, 'test-mcp', user=user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == 'Failed to load MCP prompts: All connection attempts failed'


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_rejects_disabled_server(monkeypatch):
    from open_webui.routers import tools as tools_router

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            raise AssertionError('Disabled MCP servers should not be connected.')

        async def list_prompts(self):
            raise AssertionError('Disabled MCP servers should not list prompts.')

    monkeypatch.setattr(tools_router, 'MCPClient', FakeMCPClient)

    request = build_request(
        {
            'type': 'mcp',
            'config': {'enable': False},
            'info': {'id': 'test-mcp'},
            'url': 'http://127.0.0.1:8765/mcp',
            'auth_type': 'none',
        }
    )
    user = SimpleNamespace(id='user-1')

    with pytest.raises(tools_router.HTTPException) as exc_info:
        await tools_router.get_mcp_prompt_list(request, 'test-mcp', user=user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'MCP server with id test-mcp not found'


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_rejects_access_denied(monkeypatch):
    from open_webui.routers import tools as tools_router

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            raise AssertionError('Access denied requests should not connect to MCP servers.')

        async def list_prompts(self):
            raise AssertionError('Access denied requests should not list prompts.')

    monkeypatch.setattr(tools_router, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(tools_router, 'has_connection_access', AsyncMock(return_value=False))

    request = build_request()
    user = SimpleNamespace(id='user-1')

    with pytest.raises(tools_router.HTTPException) as exc_info:
        await tools_router.get_mcp_prompt_list(request, 'test-mcp', user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == tools_router.ERROR_MESSAGES.ACCESS_PROHIBITED


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_uses_system_oauth_fallback(monkeypatch):
    from open_webui.routers import tools as tools_router
    from open_webui.utils import middleware as middleware_module

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            assert url == 'http://127.0.0.1:8765/mcp'
            assert headers == {'Authorization': 'Bearer system-token'}
            yield self

        async def list_prompts(self):
            return []

    oauth_token = {'access_token': 'system-token'}
    get_system_oauth_token = AsyncMock(return_value=oauth_token)

    monkeypatch.setattr(tools_router, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(tools_router, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(tools_router, 'get_system_oauth_token', get_system_oauth_token)
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = build_request(
        {
            'type': 'mcp',
            'config': {'enable': True},
            'info': {'id': 'test-mcp'},
            'url': 'http://127.0.0.1:8765/mcp',
            'auth_type': 'system_oauth',
        }
    )
    user = SimpleNamespace(id='user-1')

    response = await tools_router.get_mcp_prompt_list(request, 'test-mcp', user=user)

    assert response == {'prompts': []}
    get_system_oauth_token.assert_awaited_once_with(request, user)
