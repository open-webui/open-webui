import sys
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

if 'markdown' not in sys.modules:
    markdown_module = ModuleType('markdown')
    markdown_module.markdown = lambda value, *args, **kwargs: value
    sys.modules['markdown'] = markdown_module

if 'bs4' not in sys.modules:
    bs4_module = ModuleType('bs4')

    class DummyBeautifulSoup:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def find_all(self, *args, **kwargs):
            return []

    bs4_module.BeautifulSoup = DummyBeautifulSoup
    sys.modules['bs4'] = bs4_module

from open_webui.utils.mcp.client import MCPClient
from open_webui.utils.middleware import (
    insert_messages_after_system,
    normalize_mcp_prompt_messages,
)


class DummyMCPResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode=None):
        return self.payload


@pytest.mark.asyncio
async def test_list_prompts_returns_prompt_payloads():
    client = MCPClient()
    client.session = AsyncMock()
    client.session.list_prompts = AsyncMock(
        return_value=DummyMCPResult(
            {
                'prompts': [
                    {
                        'name': 'summarize',
                        'title': 'Summarize',
                        'description': 'Summarize the supplied text',
                    }
                ]
            }
        )
    )

    prompts = await client.list_prompts()

    assert prompts == [
        {
            'name': 'summarize',
            'title': 'Summarize',
            'description': 'Summarize the supplied text',
        }
    ]


@pytest.mark.asyncio
async def test_list_prompts_follows_next_cursor_until_exhausted():
    client = MCPClient()
    client.session = AsyncMock()
    client.session.list_prompts = AsyncMock(
        side_effect=[
            DummyMCPResult(
                {
                    'prompts': [{'name': 'first'}],
                    'nextCursor': 'page-2',
                }
            ),
            DummyMCPResult(
                {
                    'prompts': [{'name': 'second'}],
                }
            ),
        ]
    )

    prompts = await client.list_prompts()

    assert prompts == [{'name': 'first'}, {'name': 'second'}]
    assert client.session.list_prompts.await_args_list[0].kwargs == {'cursor': None}
    assert client.session.list_prompts.await_args_list[1].kwargs == {'cursor': 'page-2'}


@pytest.mark.asyncio
async def test_get_prompt_returns_full_result_payload():
    client = MCPClient()
    client.session = AsyncMock()
    client.session.get_prompt = AsyncMock(
        return_value=DummyMCPResult(
            {
                'description': 'Resolved prompt',
                'messages': [
                    {
                        'role': 'user',
                        'content': {'type': 'text', 'text': 'Hello'},
                    }
                ],
            }
        )
    )

    prompt = await client.get_prompt('greeting', {'name': 'Open WebUI'})

    assert prompt['description'] == 'Resolved prompt'
    assert prompt['messages'][0]['content']['text'] == 'Hello'


def test_normalize_mcp_prompt_messages_keeps_text_and_reports_omissions():
    messages, omitted_types = normalize_mcp_prompt_messages(
        {
            'messages': [
                {'role': 'user', 'content': {'type': 'text', 'text': 'Step 1'}},
                {'role': 'assistant', 'content': {'type': 'text', 'text': 'Step 2'}},
                {'role': 'assistant', 'content': {'type': 'image', 'data': '...'}},
            ]
        }
    )

    assert messages == [
        {'role': 'user', 'content': 'Step 1'},
        {'role': 'assistant', 'content': 'Step 2'},
    ]
    assert omitted_types == ['image']


def test_normalize_mcp_prompt_messages_keeps_single_user_prompt_role():
    messages, omitted_types = normalize_mcp_prompt_messages(
        {
            'messages': [
                {'role': 'user', 'content': {'type': 'text', 'text': 'Reply with PROMPT_A'}},
            ]
        }
    )

    assert messages == [{'role': 'user', 'content': 'Reply with PROMPT_A'}]
    assert omitted_types == []


def test_insert_messages_after_system_inserts_before_history():
    result = insert_messages_after_system(
        [
            {'role': 'system', 'content': 'system'},
            {'role': 'user', 'content': 'current user message'},
        ],
        [
            {'role': 'user', 'content': 'prompt user'},
            {'role': 'assistant', 'content': 'prompt assistant'},
        ],
    )

    assert result == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'prompt user'},
        {'role': 'assistant', 'content': 'prompt assistant'},
        {'role': 'user', 'content': 'current user message'},
    ]
