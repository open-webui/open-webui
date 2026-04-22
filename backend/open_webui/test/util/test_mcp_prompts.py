import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import AsyncMock
from contextlib import AsyncExitStack, asynccontextmanager

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

if 'aiocache' not in sys.modules:
    aiocache_module = ModuleType('aiocache')

    def cached(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    aiocache_module.cached = cached
    sys.modules['aiocache'] = aiocache_module

from open_webui.utils.mcp.client import MCPClient
from open_webui.utils.middleware import (
    insert_messages_before_current_user_turn,
    normalize_mcp_prompt_messages,
    process_chat_payload,
    resolve_mcp_prompt_selection,
)


class DummyMCPResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode=None):
        return self.payload


def build_process_chat_payload_request():
    model = {
        'id': 'test-model',
        'owned_by': 'openai',
        'info': {
            'meta': {
                'knowledge': False,
                'capabilities': {
                    'file_context': False,
                },
            }
        },
    }

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    TOOL_SERVER_CONNECTIONS=[
                        {
                            'type': 'mcp',
                            'info': {'id': 'test-mcp'},
                            'url': 'http://127.0.0.1:8765/mcp',
                            'auth_type': 'none',
                            'config': {'enable': True},
                        }
                    ],
                    TASK_MODEL=None,
                    TASK_MODEL_EXTERNAL=None,
                ),
                MODELS={'test-model': model},
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(direct=False, token=SimpleNamespace(credentials='token')),
    )

    return request, model


def setup_process_chat_payload_mocks(monkeypatch):
    from open_webui.utils import middleware as middleware_module

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            assert url == 'http://127.0.0.1:8765/mcp'
            assert headers in (None, {})
            yield self

        async def get_prompt(self, name, arguments=None):
            assert name == 'review_code'
            assert arguments == {'language': 'python'}
            return {
                'messages': [
                    {
                        'role': 'user',
                        'content': {'type': 'text', 'text': 'Review this Python code'},
                    }
                ]
            }

    async def passthrough_convert_url_images_to_base64(form_data):
        return form_data

    async def passthrough_process_pipeline_inlet_filter(*args, **kwargs):
        return args[1]

    async def passthrough_filter_functions(*args, **kwargs):
        return kwargs['form_data'], {}

    async def passthrough_files_handler(*args, **kwargs):
        return args[1], {'sources': []}

    monkeypatch.setattr(middleware_module, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(middleware_module, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)
    monkeypatch.setattr(middleware_module, 'apply_params_to_form_data', lambda form_data, model: form_data)
    monkeypatch.setattr(middleware_module, 'process_messages_with_output', lambda messages: messages)
    monkeypatch.setattr(middleware_module, 'apply_system_prompt_to_body', lambda *args, **kwargs: args[1])
    monkeypatch.setattr(
        middleware_module,
        'convert_url_images_to_base64',
        AsyncMock(side_effect=passthrough_convert_url_images_to_base64),
    )
    monkeypatch.setattr(middleware_module, 'get_system_oauth_token', AsyncMock(return_value=None))
    monkeypatch.setattr(middleware_module, 'get_task_model_id', lambda model_id, *args, **kwargs: model_id)
    monkeypatch.setattr(
        middleware_module,
        'process_pipeline_inlet_filter',
        AsyncMock(side_effect=passthrough_process_pipeline_inlet_filter),
    )
    monkeypatch.setattr(middleware_module, 'get_sorted_filter_ids', AsyncMock(return_value=[]))
    monkeypatch.setattr(
        middleware_module,
        'Functions',
        SimpleNamespace(get_functions_by_ids=AsyncMock(return_value=[])),
    )
    monkeypatch.setattr(
        middleware_module,
        'process_filter_functions',
        AsyncMock(side_effect=passthrough_filter_functions),
    )
    monkeypatch.setattr(
        middleware_module,
        'chat_completion_files_handler',
        AsyncMock(side_effect=passthrough_files_handler),
    )
    monkeypatch.setattr(middleware_module, 'strip_empty_content_blocks', lambda messages: messages)
    monkeypatch.setattr(middleware_module, 'merge_system_messages', lambda messages: messages)
    monkeypatch.setattr(
        middleware_module,
        'Chats',
        SimpleNamespace(get_chat_folder_id=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(
        middleware_module,
        'Folders',
        SimpleNamespace(get_folder_by_id_and_user_id=AsyncMock(return_value=None)),
    )


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


@pytest.mark.asyncio
async def test_temporary_connection_keeps_session_and_exit_stack_in_sync():
    client = MCPClient()
    previous_session = object()
    previous_exit_stack = object()
    temporary_session = object()

    client.session = previous_session
    client.exit_stack = previous_exit_stack
    client._open_session = AsyncMock(return_value=temporary_session)

    async with client.temporary_connection('http://127.0.0.1:8765/mcp'):
        assert client.session is temporary_session
        assert client.exit_stack is not previous_exit_stack
        assert isinstance(client.exit_stack, AsyncExitStack)

    assert client.session is previous_session
    assert client.exit_stack is previous_exit_stack
    client._open_session.assert_awaited_once()


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


def test_insert_messages_before_current_user_turn_keeps_prior_history_in_place():
    result = insert_messages_before_current_user_turn(
        [
            {'role': 'system', 'content': 'system'},
            {'role': 'user', 'content': 'previous user message'},
            {'role': 'assistant', 'content': 'previous assistant message'},
            {'role': 'user', 'content': 'current user message'},
        ],
        [
            {'role': 'user', 'content': 'prompt user'},
            {'role': 'assistant', 'content': 'prompt assistant'},
        ],
    )

    assert result == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'previous user message'},
        {'role': 'assistant', 'content': 'previous assistant message'},
        {'role': 'user', 'content': 'prompt user'},
        {'role': 'assistant', 'content': 'prompt assistant'},
        {'role': 'user', 'content': 'current user message'},
    ]


def test_insert_messages_before_current_user_turn_appends_when_no_user_message_exists():
    result = insert_messages_before_current_user_turn(
        [
            {'role': 'system', 'content': 'system'},
            {'role': 'assistant', 'content': 'assistant only'},
        ],
        [{'role': 'user', 'content': 'prompt user'}],
    )

    assert result == [
        {'role': 'system', 'content': 'system'},
        {'role': 'assistant', 'content': 'assistant only'},
        {'role': 'user', 'content': 'prompt user'},
    ]


@pytest.mark.asyncio
async def test_resolve_mcp_prompt_selection_fetches_prompt_without_tool_ids(monkeypatch):
    from open_webui.utils import middleware as middleware_module

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            assert url == 'http://127.0.0.1:8765/mcp'
            assert headers in (None, {})
            yield self

        async def get_prompt(self, name, arguments=None):
            assert name == 'review_code'
            assert arguments == {'language': 'python'}
            return {
                'messages': [
                    {
                        'role': 'user',
                        'content': {'type': 'text', 'text': 'Review this Python code'},
                    }
                ]
            }

    monkeypatch.setattr(middleware_module, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(middleware_module, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    TOOL_SERVER_CONNECTIONS=[
                        {
                            'type': 'mcp',
                            'info': {'id': 'test-mcp'},
                            'url': 'http://127.0.0.1:8765/mcp',
                            'auth_type': 'none',
                            'config': {'enable': True},
                        }
                    ]
                ),
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(token=SimpleNamespace(credentials='token')),
    )

    user = SimpleNamespace(id='user-1')
    metadata = {'chat_id': 'chat-1', 'message_id': 'message-1'}
    extra_params = {'__oauth_token__': None}

    messages, omitted_types = await resolve_mcp_prompt_selection(
        request,
        user,
        metadata,
        extra_params,
        {
            'server_id': 'test-mcp',
            'name': 'review_code',
            'arguments': {'language': 'python'},
        },
    )

    assert messages == [{'role': 'user', 'content': 'Review this Python code'}]
    assert omitted_types == []


@pytest.mark.asyncio
async def test_resolve_mcp_prompt_selection_rejects_disabled_server(monkeypatch):
    from open_webui.utils import middleware as middleware_module

    class FakeMCPClient:
        @asynccontextmanager
        async def temporary_connection(self, url, headers=None):
            raise AssertionError('Disabled MCP servers should not be connected.')

        async def get_prompt(self, name, arguments=None):
            raise AssertionError('Disabled MCP servers should not resolve prompts.')

    monkeypatch.setattr(middleware_module, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(middleware_module, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    TOOL_SERVER_CONNECTIONS=[
                        {
                            'type': 'mcp',
                            'info': {'id': 'test-mcp'},
                            'url': 'http://127.0.0.1:8765/mcp',
                            'auth_type': 'none',
                            'config': {'enable': False},
                        }
                    ]
                ),
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(token=SimpleNamespace(credentials='token')),
    )

    user = SimpleNamespace(id='user-1')
    metadata = {'chat_id': 'chat-1', 'message_id': 'message-1'}
    extra_params = {'__oauth_token__': None}

    with pytest.raises(Exception, match='not found or is disabled'):
        await resolve_mcp_prompt_selection(
            request,
            user,
            metadata,
            extra_params,
            {
                'server_id': 'test-mcp',
                'name': 'review_code',
                'arguments': {'language': 'python'},
            },
        )


@pytest.mark.asyncio
async def test_resolve_mcp_prompt_selection_hides_taskgroup_error_details(monkeypatch):
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

        async def get_prompt(self, name, arguments=None):
            raise AssertionError('Prompt resolution should not run after a failed connection.')

    monkeypatch.setattr(middleware_module, 'MCPClient', FakeMCPClient)
    monkeypatch.setattr(middleware_module, 'has_connection_access', AsyncMock(return_value=True))
    monkeypatch.setattr(middleware_module, 'ENABLE_FORWARD_USER_INFO_HEADERS', False)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    TOOL_SERVER_CONNECTIONS=[
                        {
                            'type': 'mcp',
                            'info': {'id': 'test-mcp'},
                            'url': 'http://127.0.0.1:8765/mcp',
                            'auth_type': 'none',
                            'config': {'enable': True},
                        }
                    ]
                ),
                oauth_client_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        state=SimpleNamespace(token=SimpleNamespace(credentials='token')),
    )

    user = SimpleNamespace(id='user-1')
    metadata = {'chat_id': 'chat-1', 'message_id': 'message-1'}
    extra_params = {'__oauth_token__': None}

    with pytest.raises(Exception, match='Failed to resolve the selected MCP prompt: All connection attempts failed'):
        await resolve_mcp_prompt_selection(
            request,
            user,
            metadata,
            extra_params,
            {
                'server_id': 'test-mcp',
                'name': 'review_code',
                'arguments': {'language': 'python'},
            },
        )


@pytest.mark.asyncio
async def test_process_chat_payload_inserts_mcp_prompt_without_tool_ids(monkeypatch):
    setup_process_chat_payload_mocks(monkeypatch)
    request, model = build_process_chat_payload_request()

    user = SimpleNamespace(id='user-1')
    form_data = {
        'model': 'test-model',
        'messages': [
            {'role': 'system', 'content': 'system'},
            {'role': 'user', 'content': 'current user message'},
        ],
    }
    metadata = {
        'mcp_prompt_selection': {
            'server_id': 'test-mcp',
            'name': 'review_code',
            'arguments': {'language': 'python'},
        }
    }

    processed_form_data, processed_metadata, events = await process_chat_payload(
        request,
        form_data,
        user,
        metadata,
        model,
    )

    assert processed_form_data['messages'] == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'Review this Python code'},
        {'role': 'user', 'content': 'current user message'},
    ]
    assert processed_metadata['tool_ids'] is None
    assert 'tools' not in processed_form_data
    assert events == []


@pytest.mark.asyncio
async def test_process_chat_payload_inserts_mcp_prompt_immediately_before_current_user_turn(
    monkeypatch,
):
    setup_process_chat_payload_mocks(monkeypatch)
    request, model = build_process_chat_payload_request()

    user = SimpleNamespace(id='user-1')
    form_data = {
        'model': 'test-model',
        'messages': [
            {'role': 'system', 'content': 'system'},
            {'role': 'user', 'content': 'previous user message'},
            {'role': 'assistant', 'content': 'previous assistant message'},
            {'role': 'user', 'content': 'current user message'},
        ],
    }
    metadata = {
        'mcp_prompt_selection': {
            'server_id': 'test-mcp',
            'name': 'review_code',
            'arguments': {'language': 'python'},
        }
    }

    processed_form_data, processed_metadata, events = await process_chat_payload(
        request,
        form_data,
        user,
        metadata,
        model,
    )

    assert processed_form_data['messages'] == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'previous user message'},
        {'role': 'assistant', 'content': 'previous assistant message'},
        {'role': 'user', 'content': 'Review this Python code'},
        {'role': 'user', 'content': 'current user message'},
    ]
    assert processed_metadata['tool_ids'] is None
    assert 'tools' not in processed_form_data
    assert events == []


@pytest.mark.asyncio
async def test_process_chat_payload_allows_explicit_tools_with_mcp_prompt_selection(monkeypatch):
    setup_process_chat_payload_mocks(monkeypatch)
    request, model = build_process_chat_payload_request()

    user = SimpleNamespace(id='user-1')
    explicit_tools = [
        {
            'type': 'function',
            'function': {
                'name': 'explicit_review_tool',
                'description': 'Review code explicitly',
                'parameters': {'type': 'object', 'properties': {}},
            },
        }
    ]
    form_data = {
        'model': 'test-model',
        'messages': [
            {'role': 'system', 'content': 'system'},
            {'role': 'user', 'content': 'current user message'},
        ],
        'tools': explicit_tools,
    }
    metadata = {
        'mcp_prompt_selection': {
            'server_id': 'test-mcp',
            'name': 'review_code',
            'arguments': {'language': 'python'},
        }
    }

    processed_form_data, processed_metadata, events = await process_chat_payload(
        request,
        form_data,
        user,
        metadata,
        model,
    )

    assert processed_form_data['messages'] == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'Review this Python code'},
        {'role': 'user', 'content': 'current user message'},
    ]
    assert processed_form_data['tools'] == explicit_tools
    assert processed_metadata['tool_ids'] is None
    assert 'tools' not in processed_metadata
    assert events == []
