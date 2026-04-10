from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_get_mcp_prompt_list_returns_argument_metadata(monkeypatch):
    from open_webui.routers import tools as tools_router

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
    monkeypatch.setattr(tools_router, 'has_connection_access', lambda user, connection: True)
    monkeypatch.setattr(tools_router, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    TOOL_SERVER_CONNECTIONS=[
                        {
                            'type': 'mcp',
                            'config': {'enable': True},
                            'info': {'id': 'test-mcp'},
                            'url': 'http://127.0.0.1:8765/mcp',
                        }
                    ]
                ),
                oauth_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(token=SimpleNamespace(credentials='token')),
        cookies={},
    )
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
