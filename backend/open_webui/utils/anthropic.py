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


def _copy_cache_control(source: dict, target: dict) -> dict:
    if isinstance(source, dict) and 'cache_control' in source:
        target['cache_control'] = source['cache_control']
    return target


def _has_cache_control(blocks: list) -> bool:
    return any(isinstance(block, dict) and 'cache_control' in block for block in blocks)


def _finalize_openai_content(blocks: list) -> str | list:
    if not blocks:
        return ''

    if len(blocks) == 1 and blocks[0].get('type') == 'text' and not _has_cache_control(blocks):
        return blocks[0].get('text', '')

    return blocks


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
            openai_content = []
            for block in system:
                if isinstance(block, dict) and block.get('type') == 'text':
                    openai_content.append(
                        _copy_cache_control(
                            block,
                            {
                                'type': 'text',
                                'text': block.get('text', ''),
                            },
                        )
                    )
                elif isinstance(block, str):
                    openai_content.append({'type': 'text', 'text': block})
            messages.append({'role': 'system', 'content': _finalize_openai_content(openai_content)})

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
                        _copy_cache_control(
                            block,
                            {
                                'type': 'text',
                                'text': block.get('text', ''),
                            },
                        )
                    )
                elif block_type == 'image':
                    source = block.get('source', {})
                    if source.get('type') == 'base64':
                        media_type = source.get('media_type', 'image/png')
                        data = source.get('data', '')
                        openai_content.append(
                            _copy_cache_control(
                                block,
                                {
                                    'type': 'image_url',
                                    'image_url': {
                                        'url': f'data:{media_type};base64,{data}',
                                    },
                                },
                            )
                        )
                    elif source.get('type') == 'url':
                        openai_content.append(
                            _copy_cache_control(
                                block,
                                {
                                    'type': 'image_url',
                                    'image_url': {'url': source.get('url', '')},
                                },
                            )
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
                                    _copy_cache_control(
                                        content_block,
                                        {
                                            'type': 'text',
                                            'text': content_block.get('text', ''),
                                        },
                                    )
                                )
                            elif content_type == 'image':
                                source = content_block.get('source', {})
                                if source.get('type') == 'base64':
                                    media_type = source.get('media_type', 'image/png')
                                    data = source.get('data', '')
                                    converted_parts.append(
                                        _copy_cache_control(
                                            content_block,
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': f'data:{media_type};base64,{data}',
                                                },
                                            },
                                        )
                                    )
                                elif source.get('type') == 'url':
                                    converted_parts.append(
                                        _copy_cache_control(
                                            content_block,
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': source.get('url', ''),
                                                },
                                            },
                                        )
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
                        if all(part.get('type') == 'text' for part in converted_parts) and not _has_cache_control(
                            converted_parts
                        ):
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
                    msg_dict['content'] = _finalize_openai_content(openai_content)
                else:
                    msg_dict['content'] = ''
                msg_dict['tool_calls'] = tool_calls
                messages.append(msg_dict)
            elif openai_content:
                messages.append({'role': role, 'content': _finalize_openai_content(openai_content)})
        else:
            messages.append({'role': role, 'content': str(content) if content else ''})

    openai_payload['messages'] = messages

    # max_tokens
    if 'max_tokens' in anthropic_payload:
        openai_payload['max_tokens'] = anthropic_payload['max_tokens']

    # Common parameters
    for param in ('temperature', 'top_p', 'top_k', 'stop_sequences', 'stream', 'metadata', 'service_tier'):
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
                _copy_cache_control(
                    tool,
                    {
                        'type': 'function',
                        'function': {
                            'name': tool.get('name', ''),
                            'description': tool.get('description', ''),
                            'parameters': tool.get('input_schema', {}),
                        },
                    },
                )
            )
        openai_payload['tools'] = openai_tools

    # tool_choice
    if 'tool_choice' in anthropic_payload:
        tool_choice = anthropic_payload['tool_choice']
        if isinstance(tool_choice, dict):
            tool_choice_type = tool_choice.get('type', 'auto')
            if tool_choice_type == 'auto':
                openai_payload['tool_choice'] = 'auto'
            elif tool_choice_type == 'any':
                openai_payload['tool_choice'] = 'required'
            elif tool_choice_type == 'tool':
                openai_payload['tool_choice'] = {
                    'type': 'function',
                    'function': {'name': tool_choice.get('name', '')},
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
    message_content = message.get('content')
    if message_content:
        content.append({'type': 'text', 'text': message_content})

    # Tool calls -> tool_use blocks
    tool_calls = message.get('tool_calls') or []
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        try:
            tool_input = json.loads(function.get('arguments', '{}'))
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
        content.append(
            {
                'type': 'tool_use',
                'id': tool_call.get('id', f'toolu_{_uuid.uuid4().hex[:24]}'),
                'name': function.get('name', ''),
                'input': tool_input,
            }
        )

    # Usage
    openai_usage = openai_response.get('usage', {})
    usage = {
        'input_tokens': openai_usage.get('prompt_tokens', 0),
        'output_tokens': openai_usage.get('completion_tokens', 0),
    }
    if 'cache_creation_input_tokens' in openai_usage:
        usage['cache_creation_input_tokens'] = openai_usage['cache_creation_input_tokens']
    if 'cache_read_input_tokens' in openai_usage:
        usage['cache_read_input_tokens'] = openai_usage['cache_read_input_tokens']

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

    Tool calls are tracked by their unique id (not OpenAI index) so that
    parallel calls sharing the same index get distinct Anthropic tool_use
    blocks. Each block follows the Anthropic lifecycle: start -> delta -> stop.
    """
    import uuid as _uuid

    message_id = f'msg_{_uuid.uuid4().hex[:24]}'
    input_tokens = 0
    output_tokens = 0
    stop_reason = 'end_turn'

    # Track content blocks with a running index.
    # Each text block or tool_use block gets its own index.
    current_block_index = 0
    text_block_open = False

    # Accumulated state for each tool call, keyed by tool call id.
    # Parallel calls that share the same OpenAI index get distinct entries.
    # Each entry: {id, name, arguments, block_index, started, stopped}
    tracked_tool_calls = {}
    # Map OpenAI tool call index -> tool call id for routing
    # argument-only deltas (deltas that carry arguments but no id).
    index_to_tool_id = {}
    # Whether any tool call block has been emitted (suppresses further text)
    has_tool_calls = False

    # Emit message_start
    message_start = {
        'type': 'message_start',
        'message': {
            'id': message_id,
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

                data_string = line[5:].strip()
                if data_string == '[DONE]':
                    continue
                if data_string == '{}':
                    continue

                try:
                    data = json.loads(data_string)
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
                # Anthropic expects text blocks before tool blocks, so skip
                # text deltas once any tool call has started.
                content = delta.get('content')
                if content and not has_tool_calls:
                    if not text_block_open:
                        block_start = {
                            'type': 'content_block_start',
                            'index': current_block_index,
                            'content_block': {'type': 'text', 'text': ''},
                        }
                        yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
                        text_block_open = True

                    block_delta = {
                        'type': 'content_block_delta',
                        'index': current_block_index,
                        'delta': {'type': 'text_delta', 'text': content},
                    }
                    yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

                # --- Handle tool calls ---
                # Some providers put tool_calls on the final message object
                # instead of the delta; fall back to that when needed.
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

                    for tool_call in tool_calls:
                        tool_call_index = tool_call.get('index', 0)
                        tool_call_id = tool_call.get('id', '')
                        tool_call_name = (tool_call.get('function') or {}).get('name', '')
                        arguments_chunk = (tool_call.get('function') or {}).get('arguments', '')

                        # Resolve which tracked tool call this delta belongs to.
                        # A delta with an id starts or identifies a specific tool.
                        # A delta without an id carries arguments for the most
                        # recent tool at this OpenAI index.
                        if tool_call_id:
                            if tool_call_id not in tracked_tool_calls:
                                tracked_tool_calls[tool_call_id] = {
                                    'id': tool_call_id,
                                    'name': tool_call_name,
                                    'arguments': '',
                                    'block_index': -1,
                                    'started': False,
                                    'stopped': False,
                                }
                            index_to_tool_id[tool_call_index] = tool_call_id
                            tool = tracked_tool_calls[tool_call_id]
                        elif tool_call_index in index_to_tool_id:
                            tool = tracked_tool_calls[index_to_tool_id[tool_call_index]]
                        else:
                            # First delta for this index with no id; create a
                            # provisional entry with a generated fallback id.
                            fallback_id = f'toolu_{_uuid.uuid4().hex[:24]}'
                            tracked_tool_calls[fallback_id] = {
                                'id': fallback_id,
                                'name': tool_call_name,
                                'arguments': '',
                                'block_index': -1,
                                'started': False,
                                'stopped': False,
                            }
                            index_to_tool_id[tool_call_index] = fallback_id
                            tool = tracked_tool_calls[fallback_id]

                        # Update name if provided on a later delta
                        if tool_call_name and not tool['name']:
                            tool['name'] = tool_call_name

                        # Emit content_block_start once we have a name
                        if not tool['started'] and tool['name']:
                            tool['block_index'] = current_block_index
                            tool['started'] = True
                            has_tool_calls = True

                            block_start = {
                                'type': 'content_block_start',
                                'index': current_block_index,
                                'content_block': {
                                    'type': 'tool_use',
                                    'id': tool['id'],
                                    'name': tool['name'],
                                    'input': {},
                                },
                            }
                            yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
                            current_block_index += 1

                        # Buffer arguments and emit as input_json_delta
                        if arguments_chunk:
                            tool['arguments'] += arguments_chunk

                            if tool['started'] and not tool['stopped']:
                                block_delta = {
                                    'type': 'content_block_delta',
                                    'index': tool['block_index'],
                                    'delta': {
                                        'type': 'input_json_delta',
                                        'partial_json': arguments_chunk,
                                    },
                                }
                                yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

                            # Close the block once arguments form complete JSON
                            if tool['started'] and not tool['stopped']:
                                try:
                                    json.loads(tool['arguments'])
                                    tool['stopped'] = True
                                    block_stop = {
                                        'type': 'content_block_stop',
                                        'index': tool['block_index'],
                                    }
                                    yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()
                                except (json.JSONDecodeError, ValueError):
                                    pass

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

    # Flush any tools that buffered arguments but never emitted a block
    for tool in tracked_tool_calls.values():
        if not tool['started'] and tool['name']:
            tool['block_index'] = current_block_index
            tool['started'] = True

            block_start = {
                'type': 'content_block_start',
                'index': current_block_index,
                'content_block': {
                    'type': 'tool_use',
                    'id': tool['id'],
                    'name': tool['name'],
                    'input': {},
                },
            }
            yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
            current_block_index += 1

            if tool['arguments']:
                block_delta = {
                    'type': 'content_block_delta',
                    'index': tool['block_index'],
                    'delta': {
                        'type': 'input_json_delta',
                        'partial_json': tool['arguments'],
                    },
                }
                yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

    # Close any open text block
    if text_block_open:
        block_stop = {'type': 'content_block_stop', 'index': current_block_index}
        yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()

    # Close any tool call blocks that are still open
    for tool in tracked_tool_calls.values():
        if tool['started'] and not tool['stopped']:
            block_stop = {'type': 'content_block_stop', 'index': tool['block_index']}
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
