import json
import logging

import aiohttp
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.models.users import UserModel
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def is_anthropic_url(url: str) -> bool:
    """Check if the URL is an Anthropic API endpoint."""
    return 'api.anthropic.com' in url


async def get_anthropic_models(url: str, key: str, user: UserModel = None) -> dict:
    """
    Fetch models from Anthropic's /v1/models endpoint with pagination.
    Normalizes the response to OpenAI format.
    """
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    all_models = []
    after_id = None

    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            while True:
                params = {'limit': 1000}
                if after_id:
                    params['after_id'] = after_id

                async with session.get(
                    f'{url}/models',
                    headers=headers,
                    params=params,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status != 200:
                        error_detail = f'HTTP Error: {response.status}'
                        try:
                            res = await response.json()
                            if 'error' in res:
                                error_detail = f'External Error: {res["error"]}'
                        except Exception:
                            pass
                        return {'object': 'list', 'data': [], 'error': error_detail}

                    data = await response.json()

                    for model in data.get('data', []):
                        all_models.append(
                            {
                                'id': model.get('id'),
                                'object': 'model',
                                'created': 0,
                                'owned_by': 'anthropic',
                                'name': model.get('display_name', model.get('id')),
                            }
                        )

                    if not data.get('has_more', False):
                        break
                    after_id = data.get('last_id')

    except Exception as e:
        log.error(f'Anthropic connection error: {e}')
        return None

    return {'object': 'list', 'data': all_models}


##############################
#
# Anthropic Messages API Conversion Utilities
#
##############################


def convert_anthropic_to_openai_payload(anthropic_payload: dict) -> dict:
    """
    Convert an Anthropic Messages API request to OpenAI Chat Completions format.

    Anthropic format:
        {model, messages: [{role, content}], system, max_tokens, ...}
    OpenAI format:
        {model, messages: [{role, content}], max_tokens, ...}
    """
    openai_payload = {}

    # Model
    openai_payload['model'] = anthropic_payload.get('model', '')

    # Build messages list
    messages = []

    # System prompt (Anthropic has it as top-level, OpenAI as a system message)
    system = anthropic_payload.get('system')
    if system:
        if isinstance(system, str):
            messages.append({'role': 'system', 'content': system})
        elif isinstance(system, list):
            # Anthropic supports system as list of content blocks
            text_parts = []
            for block in system:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
                elif isinstance(block, str):
                    text_parts.append(block)
            messages.append({'role': 'system', 'content': '\n'.join(text_parts)})

    # Convert messages
    for msg in anthropic_payload.get('messages', []):
        role = msg.get('role', 'user')
        content = msg.get('content')

        if isinstance(content, str):
            messages.append({'role': role, 'content': content})
        elif isinstance(content, list):
            # Convert Anthropic content blocks to OpenAI format
            openai_content = []
            tool_calls = []

            for block in content:
                block_type = block.get('type', 'text')

                if block_type == 'text':
                    openai_content.append(
                        {
                            'type': 'text',
                            'text': block.get('text', ''),
                        }
                    )
                elif block_type == 'image':
                    source = block.get('source', {})
                    if source.get('type') == 'base64':
                        media_type = source.get('media_type', 'image/png')
                        data = source.get('data', '')
                        openai_content.append(
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:{media_type};base64,{data}',
                                },
                            }
                        )
                    elif source.get('type') == 'url':
                        openai_content.append(
                            {
                                'type': 'image_url',
                                'image_url': {'url': source.get('url', '')},
                            }
                        )
                elif block_type == 'tool_use':
                    tool_calls.append(
                        {
                            'id': block.get('id', ''),
                            'type': 'function',
                            'function': {
                                'name': block.get('name', ''),
                                'arguments': (
                                    json.dumps(block.get('input', {}))
                                    if isinstance(block.get('input'), dict)
                                    else str(block.get('input', '{}'))
                                ),
                            },
                        }
                    )
                elif block_type == 'tool_result':
                    # Tool results become separate tool messages in OpenAI format
                    tool_result_content = block.get('content', '')
                    tool_content: str | list = ''

                    if isinstance(tool_result_content, str):
                        tool_content = tool_result_content
                    elif isinstance(tool_result_content, list):
                        # Build a multimodal content array to preserve
                        # images and other non-text content types.
                        converted_parts = []
                        for content_block in tool_result_content:
                            if not isinstance(content_block, dict):
                                continue
                            content_type = content_block.get('type', 'text')

                            if content_type == 'text':
                                converted_parts.append(
                                    {
                                        'type': 'text',
                                        'text': content_block.get('text', ''),
                                    }
                                )
                            elif content_type == 'image':
                                source = content_block.get('source', {})
                                if source.get('type') == 'base64':
                                    media_type = source.get('media_type', 'image/png')
                                    data = source.get('data', '')
                                    converted_parts.append(
                                        {
                                            'type': 'image_url',
                                            'image_url': {
                                                'url': f'data:{media_type};base64,{data}',
                                            },
                                        }
                                    )
                                elif source.get('type') == 'url':
                                    converted_parts.append(
                                        {
                                            'type': 'image_url',
                                            'image_url': {
                                                'url': source.get('url', ''),
                                            },
                                        }
                                    )
                            elif content_type == 'document':
                                # Documents have no direct OpenAI equivalent;
                                # convert to a text representation.
                                document_source = content_block.get('source', {})
                                document_title = content_block.get('title', 'Document')
                                document_context = content_block.get('context', '')
                                document_text = f'[Document: {document_title}]'
                                if document_context:
                                    document_text += f'\n{document_context}'
                                if document_source.get('type') == 'text' and document_source.get('data'):
                                    document_text += f'\n{document_source["data"]}'
                                converted_parts.append({'type': 'text', 'text': document_text})
                            elif content_type == 'search_result':
                                # Convert search results to a text
                                # representation with source attribution.
                                search_title = content_block.get('title', '')
                                search_url = content_block.get('source', '')
                                search_content_blocks = content_block.get('content', [])
                                search_texts = []
                                for search_block in search_content_blocks:
                                    if isinstance(search_block, dict) and search_block.get('type') == 'text':
                                        search_texts.append(search_block.get('text', ''))
                                search_body = '\n'.join(search_texts)
                                search_text = f'[Search Result: {search_title}]'
                                if search_url:
                                    search_text += f'\nSource: {search_url}'
                                if search_body:
                                    search_text += f'\n{search_body}'
                                converted_parts.append({'type': 'text', 'text': search_text})

                        # Flatten to string when only text parts are present
                        if all(part.get('type') == 'text' for part in converted_parts):
                            tool_content = '\n'.join(part.get('text', '') for part in converted_parts)
                        elif converted_parts:
                            tool_content = converted_parts
                        else:
                            tool_content = ''

                    # Propagate error status if present
                    if block.get('is_error'):
                        if isinstance(tool_content, str):
                            tool_content = f'Error: {tool_content}'
                        elif isinstance(tool_content, list):
                            tool_content.insert(
                                0,
                                {
                                    'type': 'text',
                                    'text': 'Error: ',
                                },
                            )

                    messages.append(
                        {
                            'role': 'tool',
                            'tool_call_id': block.get('tool_use_id', ''),
                            'content': tool_content,
                        }
                    )

            # Build the message
            if tool_calls:
                # Assistant message with tool calls
                msg_dict = {'role': role}
                if openai_content:
                    # If there's only text, flatten it
                    if len(openai_content) == 1 and openai_content[0]['type'] == 'text':
                        msg_dict['content'] = openai_content[0]['text']
                    else:
                        msg_dict['content'] = openai_content
                else:
                    msg_dict['content'] = ''
                msg_dict['tool_calls'] = tool_calls
                messages.append(msg_dict)
            elif openai_content:
                # If there's only a single text block, flatten it to a string
                if len(openai_content) == 1 and openai_content[0]['type'] == 'text':
                    messages.append({'role': role, 'content': openai_content[0]['text']})
                else:
                    messages.append({'role': role, 'content': openai_content})
        else:
            messages.append({'role': role, 'content': str(content) if content else ''})

    openai_payload['messages'] = messages

    # max_tokens
    if 'max_tokens' in anthropic_payload:
        openai_payload['max_tokens'] = anthropic_payload['max_tokens']

    # Common parameters
    for param in ('temperature', 'top_p', 'stop_sequences', 'stream'):
        if param in anthropic_payload:
            if param == 'stop_sequences':
                openai_payload['stop'] = anthropic_payload[param]
            else:
                openai_payload[param] = anthropic_payload[param]

    # Tools conversion: Anthropic → OpenAI
    if 'tools' in anthropic_payload:
        openai_tools = []
        for tool in anthropic_payload['tools']:
            openai_tools.append(
                {
                    'type': 'function',
                    'function': {
                        'name': tool.get('name', ''),
                        'description': tool.get('description', ''),
                        'parameters': tool.get('input_schema', {}),
                    },
                }
            )
        openai_payload['tools'] = openai_tools

    # tool_choice
    if 'tool_choice' in anthropic_payload:
        tc = anthropic_payload['tool_choice']
        if isinstance(tc, dict):
            tc_type = tc.get('type', 'auto')
            if tc_type == 'auto':
                openai_payload['tool_choice'] = 'auto'
            elif tc_type == 'any':
                openai_payload['tool_choice'] = 'required'
            elif tc_type == 'tool':
                openai_payload['tool_choice'] = {
                    'type': 'function',
                    'function': {'name': tc.get('name', '')},
                }

    return openai_payload


def convert_openai_to_anthropic_response(openai_response: dict, model: str = '') -> dict:
    """
    Convert a non-streaming OpenAI Chat Completions response to Anthropic Messages format.
    """
    import uuid as _uuid

    choice = {}
    if openai_response.get('choices'):
        choice = openai_response['choices'][0]

    message = choice.get('message', {})
    finish_reason = choice.get('finish_reason', 'stop')

    # Map finish_reason to stop_reason
    stop_reason_map = {
        'stop': 'end_turn',
        'length': 'max_tokens',
        'tool_calls': 'tool_use',
        'content_filter': 'end_turn',
    }
    stop_reason = stop_reason_map.get(finish_reason, 'end_turn')

    # Build content blocks
    content = []
    msg_content = message.get('content')
    if msg_content:
        content.append({'type': 'text', 'text': msg_content})

    # Tool calls → tool_use blocks
    tool_calls = message.get('tool_calls', [])
    for tc in tool_calls:
        func = tc.get('function', {})
        try:
            tool_input = json.loads(func.get('arguments', '{}'))
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
        content.append(
            {
                'type': 'tool_use',
                'id': tc.get('id', f'toolu_{_uuid.uuid4().hex[:24]}'),
                'name': func.get('name', ''),
                'input': tool_input,
            }
        )

    # Usage
    openai_usage = openai_response.get('usage', {})
    usage = {
        'input_tokens': openai_usage.get('prompt_tokens', 0),
        'output_tokens': openai_usage.get('completion_tokens', 0),
    }

    return {
        'id': openai_response.get('id', f'msg_{_uuid.uuid4().hex[:24]}'),
        'type': 'message',
        'role': 'assistant',
        'content': content,
        'model': model or openai_response.get('model', ''),
        'stop_reason': stop_reason,
        'stop_sequence': None,
        'usage': usage,
    }


async def openai_stream_to_anthropic_stream(openai_stream_generator, model: str = ''):
    """
    Convert an OpenAI SSE streaming response to Anthropic Messages SSE format.

    OpenAI sends: data: {"choices": [{"delta": {"content": "..."}}]}
    Anthropic sends: event: content_block_delta\\ndata: {"type": "content_block_delta", ...}

    Handles text content, tool calls, and mixed content with proper
    multi-block indexing as required by Anthropic's streaming protocol.
    """
    import uuid as _uuid

    msg_id = f'msg_{_uuid.uuid4().hex[:24]}'
    input_tokens = 0
    output_tokens = 0
    stop_reason = 'end_turn'

    # Track content blocks with a running index.
    # Each text block or tool_use block gets its own index.
    current_block_index = 0
    text_block_open = False

    # Track tool call state by tool id when available so parallel calls that
    # reuse the same OpenAI index still get distinct Anthropic content blocks.
    tool_call_started: set[str] = set()
    pending_tools: dict[str, dict] = {}
    # OpenAI index -> ordered stream keys (parallel calls sharing one index in a batch).
    index_stream_order: dict[int, list[str]] = {}
    # OpenAI index -> stream key currently receiving id-less argument deltas.
    index_active_stream: dict[int, str] = {}

    def _register_stream_key(tc_index: int, stream_key: str) -> None:
        order = index_stream_order.setdefault(tc_index, [])
        if stream_key not in order:
            order.append(stream_key)

    def _migrate_placeholder(tc_index: int, tc_id: str) -> None:
        placeholder = f'openai_index:{tc_index}'
        if placeholder in pending_tools and not pending_tools[placeholder]['started']:
            state = pending_tools.pop(placeholder)
            state['stream_key'] = tc_id
            state['id'] = tc_id
            pending_tools[tc_id] = state

    def _resolve_stream_key(
        tc: dict,
        batch_position: int | None,
        multi_same_index_in_delta: bool,
    ) -> str:
        tc_index = tc.get('index', 0)
        tc_id = tc.get('id') or ''
        tc_name = (tc.get('function') or {}).get('name', '') or ''

        if tc_id:
            _migrate_placeholder(tc_index, tc_id)
            return tc_id

        order = index_stream_order.get(tc_index, [])

        # Multiple tool_calls in one delta sharing the same index (non-standard).
        if multi_same_index_in_delta and batch_position is not None:
            if batch_position < len(order):
                return order[batch_position]
            return f'openai_index:{tc_index}:{batch_position}'

        # Standard OpenAI: one entry per delta — route args to the active tool at this index.
        active = index_active_stream.get(tc_index)
        if active and active in pending_tools:
            return active

        if len(order) == 1:
            return order[0]

        if tc_index in index_active_stream:
            return index_active_stream[tc_index]

        if tc_name:
            slot_num = len(order)
            return f'openai_index:{tc_index}:{slot_num}'

        provisional = f'openai_index:{tc_index}'
        if provisional in pending_tools:
            return provisional

        return f'openai_index:{tc_index}:{batch_position or 0}'

    def _process_tool_call(
        tc: dict,
        batch_position: int | None,
        multi_same_index_in_delta: bool,
    ) -> list[bytes]:
        events: list[bytes] = []
        tc_index = tc.get('index', 0)
        stream_key = _resolve_stream_key(
            tc,
            batch_position,
            multi_same_index_in_delta,
        )

        if stream_key not in pending_tools:
            pending_tools[stream_key] = {
                'stream_key': stream_key,
                'tc_index': tc_index,
                'id': '',
                'name': '',
                'arguments': '',
                'started': False,
                'stopped': False,
            }

        state = pending_tools[stream_key]

        if tc.get('id'):
            state['id'] = tc['id']
            if tc['id'] != stream_key:
                pending_tools.pop(stream_key, None)
                state['stream_key'] = tc['id']
                pending_tools[tc['id']] = state
                stream_key = tc['id']

        _register_stream_key(tc_index, stream_key)
        state = pending_tools[stream_key]

        tc_name = (tc.get('function') or {}).get('name', '') or ''
        if tc_name:
            state['name'] = tc_name

        args_chunk = (tc.get('function') or {}).get('arguments', '') or ''
        if args_chunk:
            events.extend(_append_tool_arguments(state, args_chunk))

        return events

    def _tool_arguments_complete(arguments: str) -> bool:
        if not arguments:
            return False
        try:
            json.loads(arguments)
            return True
        except json.JSONDecodeError:
            return False

    def _emit_tool_block_stop(state: dict) -> list[bytes]:
        if not state.get('started') or state.get('stopped'):
            return []
        state['stopped'] = True
        return [
            f'event: content_block_stop\ndata: {json.dumps({"type": "content_block_stop", "index": state["block_index"]})}\n\n'.encode()
        ]

    def _close_other_open_tools(current_stream_key: str) -> list[bytes]:
        events: list[bytes] = []
        for other in pending_tools.values():
            if other.get('started') and not other.get('stopped') and other['stream_key'] != current_stream_key:
                events.extend(_emit_tool_block_stop(other))
        return events

    def _emit_tool_block_start(state: dict) -> list[bytes]:
        nonlocal current_block_index

        events = _close_other_open_tools(state['stream_key'])

        tool_id = state['id'] or f'toolu_{_uuid.uuid4().hex[:24]}'
        block_index = current_block_index

        state['block_index'] = block_index
        state['started'] = True
        tool_call_started.add(state['stream_key'])
        index_active_stream[state['tc_index']] = state['stream_key']

        events.append(
            f'event: content_block_start\ndata: {json.dumps({"type": "content_block_start", "index": block_index, "content_block": {"type": "tool_use", "id": tool_id, "name": state["name"], "input": {}}})}\n\n'.encode()
        )
        current_block_index += 1
        return events

    def _append_tool_arguments(state: dict, args_chunk: str) -> list[bytes]:
        events: list[bytes] = []

        if not args_chunk:
            return events

        if not state['name'].strip():
            state['arguments'] += args_chunk
            return events

        if not state['started']:
            events.extend(_emit_tool_block_start(state))

        if state.get('stopped'):
            return events

        state['arguments'] += args_chunk
        block_delta = {
            'type': 'content_block_delta',
            'index': state['block_index'],
            'delta': {
                'type': 'input_json_delta',
                'partial_json': args_chunk,
            },
        }
        events.append(f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode())

        if _tool_arguments_complete(state['arguments']):
            events.extend(_emit_tool_block_stop(state))

        return events

    # Emit message_start
    message_start = {
        'type': 'message_start',
        'message': {
            'id': msg_id,
            'type': 'message',
            'role': 'assistant',
            'content': [],
            'model': model,
            'stop_reason': None,
            'stop_sequence': None,
            'usage': {'input_tokens': 0, 'output_tokens': 0},
        },
    }
    yield f'event: message_start\ndata: {json.dumps(message_start)}\n\n'.encode()

    try:
        async for chunk in openai_stream_generator:
            if isinstance(chunk, bytes):
                chunk = chunk.decode('utf-8', errors='ignore')

            for line in chunk.strip().split('\n'):
                line = line.strip()

                if not line or not line.startswith('data:'):
                    continue

                data_str = line[5:].strip()
                if data_str == '[DONE]':
                    continue
                if data_str == '{}':
                    continue

                try:
                    data = json.loads(data_str)
                except (json.JSONDecodeError, TypeError):
                    continue

                choices = data.get('choices', [])
                if not choices:
                    # Check for usage in the final chunk
                    if data.get('usage'):
                        input_tokens = data['usage'].get('prompt_tokens', input_tokens)
                        output_tokens = data['usage'].get('completion_tokens', output_tokens)
                    continue

                delta = choices[0].get('delta', {})
                finish_reason = choices[0].get('finish_reason')
                message = choices[0].get('message') or {}

                # Update usage if present
                if data.get('usage'):
                    input_tokens = data['usage'].get('prompt_tokens', input_tokens)
                    output_tokens = data['usage'].get('completion_tokens', output_tokens)

                # --- Handle text content ---
                content = delta.get('content')
                if content and not tool_call_started:
                    if not text_block_open:
                        # Start a new text content block
                        block_start = {
                            'type': 'content_block_start',
                            'index': current_block_index,
                            'content_block': {'type': 'text', 'text': ''},
                        }
                        yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
                        text_block_open = True

                    # Send text delta
                    block_delta = {
                        'type': 'content_block_delta',
                        'index': current_block_index,
                        'delta': {'type': 'text_delta', 'text': content},
                    }
                    yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

                # --- Handle tool calls ---
                tool_calls = delta.get('tool_calls') or []
                if not tool_calls and message.get('tool_calls'):
                    tool_calls = message['tool_calls']

                if tool_calls:
                    # Close text block if one is open (text comes before tools)
                    if text_block_open:
                        block_stop = {
                            'type': 'content_block_stop',
                            'index': current_block_index,
                        }
                        yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()
                        text_block_open = False
                        current_block_index += 1

                    index_counts: dict[int, int] = {}
                    for tc in tool_calls:
                        tc_index = tc.get('index', 0)
                        index_counts[tc_index] = index_counts.get(tc_index, 0) + 1

                    index_batch_positions: dict[int, int] = {}
                    for tc in tool_calls:
                        tc_index = tc.get('index', 0)
                        batch_position = index_batch_positions.get(tc_index, 0)
                        index_batch_positions[tc_index] = batch_position + 1
                        multi_same_index = index_counts.get(tc_index, 0) > 1
                        for event in _process_tool_call(tc, batch_position, multi_same_index):
                            yield event

                # --- Handle finish reason ---
                if finish_reason is not None:
                    stop_reason_map = {
                        'stop': 'end_turn',
                        'length': 'max_tokens',
                        'tool_calls': 'tool_use',
                    }
                    stop_reason = stop_reason_map.get(finish_reason, 'end_turn')

    except Exception as e:
        log.error(f'Error in Anthropic stream conversion: {e}')

    for state in list(pending_tools.values()):
        if not state['started'] and state['name'].strip():
            for event in _emit_tool_block_start(state):
                yield event
            if state['started'] and not state.get('stopped'):
                for event in _emit_tool_block_stop(state):
                    yield event

    for state in pending_tools.values():
        if state['started'] and not state.get('stopped'):
            for event in _emit_tool_block_stop(state):
                yield event

    # Close any open text block
    if text_block_open:
        block_stop = {'type': 'content_block_stop', 'index': current_block_index}
        yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()

    # Emit message_delta with stop reason
    message_delta = {
        'type': 'message_delta',
        'delta': {
            'stop_reason': stop_reason,
            'stop_sequence': None,
        },
        'usage': {'output_tokens': output_tokens},
    }
    yield f'event: message_delta\ndata: {json.dumps(message_delta)}\n\n'.encode()

    # Emit message_stop
    yield f'event: message_stop\ndata: {json.dumps({"type": "message_stop"})}\n\n'.encode()
