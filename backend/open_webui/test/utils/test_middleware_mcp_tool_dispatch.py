"""Regression test for open-webui/open-webui#26860.

"native MCP tool call is not dispatched": when an OpenAI-compatible
provider (e.g. vLLM, and per public reports also Ollama's own
OpenAI-compat endpoint) streams a `tool_calls` delta WITHOUT an
`index` field -- unlike OpenAI's own API, which always populates it --
`streaming_chat_response_handler`'s delta accumulator used to silently
discard the delta (it only accumulated when
`delta_tool_call.get('index') is not None`). The tool call was never
added to `response_tool_calls`, so it was never queued for dispatch,
and the configured MCP tool's `callable` was never invoked: no
exception, no timeout, just an indefinitely hanging chat -- exactly
matching the symptom reported in #26860.

This test drives the real `streaming_chat_response_handler` with a
fake upstream SSE stream shaped like that non-conformant delta
(tool_calls chunks with no `index` key at all) and a mocked MCP tool
registered in `metadata['tools']` the same way
`connect_mcp_server()`/the tool_ids loop in `process_chat_payload`
would register it. It asserts the mocked MCP tool actually gets
invoked with the parsed arguments once the stream completes.
"""

import json
import types
from unittest.mock import AsyncMock, patch

import pytest


def _fake_request():
    request = types.SimpleNamespace()
    request.state = types.SimpleNamespace()
    request.cookies = {}
    request.app = types.SimpleNamespace(state=types.SimpleNamespace())
    return request


def _fake_response(chunks):
    async def body_iterator():
        for chunk in chunks:
            yield f'data: {json.dumps(chunk)}\n\n'

    response = types.SimpleNamespace()
    response.body_iterator = body_iterator()
    response.background = None
    return response


@pytest.mark.asyncio
async def test_mcp_tool_dispatched_when_delta_omits_index():
    """The MCP tool is invoked even when tool_call deltas lack `index`."""
    from open_webui.utils import middleware

    mcp_tool_calls = []

    async def mcp_tool_callable(**kwargs):
        mcp_tool_calls.append(kwargs)
        return {'status': 'ok', 'echo': kwargs.get('msg')}

    tool_name = 'server-1_echo_tool'

    # Mirrors exactly what the tool_ids loop in process_chat_payload /
    # connect_mcp_server() puts into metadata['tools'] for an MCP tool.
    metadata = {
        'chat_id': 'test-chat-id',
        'message_id': 'test-message-id',
        'session_id': 'test-session-id',
        'params': {},
        'tools': {
            tool_name: {
                'spec': {
                    'name': tool_name,
                    'description': 'Echoes a message.',
                    'parameters': {
                        'type': 'object',
                        'properties': {'msg': {'type': 'string'}},
                    },
                },
                'callable': mcp_tool_callable,
                'type': 'mcp',
                'direct': False,
            }
        },
    }

    form_data = {
        'model': 'test-model',
        'messages': [{'role': 'user', 'content': 'call the echo tool'}],
        'tools': [{'type': 'function', 'function': metadata['tools'][tool_name]['spec']}],
    }

    model = {'id': 'test-model', 'info': {'meta': {}}}
    user = types.SimpleNamespace(id='test-user-id')
    request = _fake_request()

    events_emitted = []

    async def event_emitter(event):
        events_emitted.append(event)

    async def event_caller(event):
        return None

    ctx = {
        'request': request,
        'form_data': form_data,
        'user': user,
        'model': model,
        'metadata': metadata,
        'tasks': None,
        'events': [],
        'event_emitter': event_emitter,
        'event_caller': event_caller,
    }

    # First chunk introduces the tool call (id/type/name) but -- like the
    # vLLM/Ollama-OpenAI-compat payloads reported upstream -- omits `index`
    # entirely. Second chunk streams the arguments, also without `index`.
    response = _fake_response(
        [
            {
                'choices': [
                    {
                        'delta': {
                            'tool_calls': [
                                {
                                    'id': 'call_1',
                                    'type': 'function',
                                    'function': {'name': tool_name, 'arguments': ''},
                                }
                            ]
                        },
                        'finish_reason': None,
                    }
                ]
            },
            {
                'choices': [
                    {
                        'delta': {
                            'tool_calls': [
                                {'function': {'arguments': json.dumps({'msg': 'hi'})}},
                            ]
                        },
                        'finish_reason': None,
                    }
                ]
            },
            {'choices': [{'delta': {}, 'finish_reason': 'tool_calls'}]},
        ]
    )

    with (
        patch.object(
            middleware,
            'Chats',
            new=types.SimpleNamespace(
                upsert_message_to_chat_by_id_and_message_id=AsyncMock(return_value=None),
                add_message_files_by_id_and_message_id=AsyncMock(return_value=None),
                get_chat_title_by_id=AsyncMock(return_value='Test Chat'),
                get_message_by_id_and_message_id=AsyncMock(return_value=None),
            ),
        ),
        patch.object(
            middleware,
            'Config',
            new=types.SimpleNamespace(
                get=AsyncMock(return_value=False),
                get_many=AsyncMock(return_value={}),
            ),
        ),
        patch.object(
            middleware,
            'Users',
            new=types.SimpleNamespace(
                is_user_active=AsyncMock(return_value=True),
                get_user_webhook_url_by_id=AsyncMock(return_value=None),
            ),
        ),
        patch.object(middleware, 'get_sorted_filter_ids', new=AsyncMock(return_value=[])),
        patch.object(middleware, 'background_tasks_handler', new=AsyncMock(return_value=None)),
        patch.object(middleware, 'outlet_filter_handler', new=AsyncMock(return_value=None)),
    ):
        await middleware.streaming_chat_response_handler(response, ctx)

    assert mcp_tool_calls == [{'msg': 'hi'}], (
        'MCP tool was never dispatched: the streamed tool_calls delta lacked '
        'an `index` field, and streaming_chat_response_handler silently '
        'dropped it instead of dispatching the tool call.'
    )
