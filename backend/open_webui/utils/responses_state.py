"""Shared stateful Responses API policy used by routing and chat middleware."""

RESPONSES_TERMINAL_STATUSES = frozenset({'completed', 'failed', 'cancelled', 'incomplete'})
RESPONSES_LIFECYCLE_EVENTS = frozenset(
    {
        'response.cancelled',
        'response.completed',
        'response.created',
        'response.failed',
        'response.in_progress',
        'response.incomplete',
        'response.queued',
    }
)
RESPONSES_LOCAL_ITEM_FIELDS = frozenset(
    {
        '_tag_type',
        'attributes',
        'duration',
        'end_tag',
        'ended_at',
        'start_tag',
        'started_at',
    }
)


def get_stateful_response_id(messages_map: dict, user_message_id: str, model_id: str | None) -> str | None:
    """Return the response anchor for the branch containing *user_message_id*."""
    user_message = messages_map.get(user_message_id)
    if not isinstance(user_message, dict) or user_message.get('role') != 'user':
        return None

    parent = messages_map.get(user_message.get('parentId'))
    if not isinstance(parent, dict) or parent.get('role') != 'assistant':
        return None

    parent_model = parent.get('selectedModelId') or parent.get('model')
    if parent_model and parent_model != model_id:
        return None

    response_id = parent.get('responseId') or parent.get('response_id')
    return response_id if isinstance(response_id, str) and response_id else None


def get_openai_url_idx(model: dict, models: dict) -> int | None:
    """Resolve an OpenAI connection index for base models and custom profiles."""
    connection_model = model
    if connection_model.get('urlIdx') is None:
        base_model_id = (model.get('info') or {}).get('base_model_id')
        connection_model = models.get(base_model_id, {})

    url_idx = connection_model.get('urlIdx')
    return url_idx if isinstance(url_idx, int) else None


def apply_responses_stateful_payload(payload: dict, is_responses: bool, enabled: bool) -> dict:
    """Apply stateful-only fields after the target API type is known."""
    if is_responses:
        if payload.get('conversation') is not None and payload.get('previous_response_id'):
            raise ValueError('conversation and previous_response_id cannot be used together')
        if enabled:
            payload['store'] = True
    elif not is_responses:
        payload.pop('previous_response_id', None)
    return payload


def trim_stateful_messages(messages: list[dict], regeneration: bool = False) -> list[dict]:
    """Keep only instructions and input not already represented by the response anchor."""
    system_message = next((message for message in messages if message.get('role') == 'system'), None)
    user_messages = [message for message in messages if message.get('role') == 'user']
    current_input = user_messages[-2:] if regeneration and len(user_messages) > 1 else user_messages[-1:]
    return ([system_message] if system_message else []) + current_input


def get_response_metadata(response: dict) -> dict:
    """Return response-level state carried by a Responses lifecycle event."""
    status = response.get('status')
    metadata = {
        'usage': response.get('usage'),
        'response_id': response.get('id'),
        'response_status': status,
    }
    if status in RESPONSES_TERMINAL_STATUSES:
        metadata['done'] = True
    if response.get('error') is not None:
        metadata['error'] = response['error']
    if response.get('incomplete_details') is not None:
        metadata['incomplete_details'] = response['incomplete_details']
    return metadata


def handle_responses_lifecycle_event(
    event_type: str,
    response: dict,
    current_output: list[dict],
) -> tuple[list[dict], dict] | None:
    """Apply a Responses lifecycle event without interpreting output item types."""
    if event_type not in RESPONSES_LIFECYCLE_EVENTS:
        return None

    final_output = response.get('output')
    output = final_output if final_output else current_output
    if event_type == 'response.completed':
        output = [
            {**item, 'status': 'completed'}
            if item.get('type') == 'reasoning' and item.get('status') != 'completed'
            else item
            for item in output
        ]
    return output, get_response_metadata(response)


def normalize_responses_input_item(item: dict) -> dict | None:
    """Remove OpenWebUI-only fields while preserving native Responses item fields."""
    item_type = item.get('type', '')
    if item_type.startswith('open_webui:'):
        return None

    normalized = dict(item)
    if item_type in {'message', 'reasoning', 'function_call', 'function_call_output'}:
        normalized = {key: value for key, value in normalized.items() if key not in RESPONSES_LOCAL_ITEM_FIELDS}
    if item_type == 'function_call_output':
        return {key: normalized[key] for key in ('type', 'call_id', 'output') if key in normalized}
    if item_type == 'function_call':
        normalized.pop('approved', None)
    return normalized


def _convert_responses_content_part(part: dict, role: str) -> dict | None:
    part_type = part.get('type')
    text_type = 'output_text' if role == 'assistant' else 'input_text'
    if part_type == 'text':
        return {'type': text_type, 'text': part.get('text', '')}
    if part_type == 'image_url':
        image = part.get('image_url', {})
        if isinstance(image, dict):
            image_url = image.get('url', '')
            detail = image.get('detail') or 'auto'
        else:
            image_url = image if isinstance(image, str) else ''
            detail = 'auto'
        return {'type': 'input_image', 'image_url': image_url, 'detail': detail}
    if part_type == 'file':
        file = part.get('file')
        if not isinstance(file, dict):
            return None
        file_part = {key: file[key] for key in ('file_id', 'file_data', 'filename') if key in file}
        return {'type': 'input_file', **file_part} if {'file_id', 'file_data'} & file_part.keys() else None
    return dict(part)


def _convert_responses_tool_choice(tool_choice):
    if not isinstance(tool_choice, dict) or tool_choice.get('type') != 'function':
        return tool_choice
    function = tool_choice.get('function')
    if isinstance(function, dict):
        return {'type': 'function', 'name': function.get('name', '')}
    return tool_choice


def _convert_responses_text_config(payload: dict) -> None:
    response_format = payload.pop('response_format', None)
    if not isinstance(response_format, dict):
        return

    format_type = response_format.get('type')
    if format_type == 'json_schema' and isinstance(response_format.get('json_schema'), dict):
        text_format = {'type': 'json_schema', **response_format['json_schema']}
    else:
        text_format = dict(response_format)
    payload['text'] = {**(payload.get('text') or {}), 'format': text_format}


def _convert_message_content(content, role: str) -> list[dict]:
    text_type = 'output_text' if role == 'assistant' else 'input_text'
    if isinstance(content, str):
        return [{'type': text_type, 'text': content}]
    if isinstance(content, list):
        return [
            converted
            for part in content
            if isinstance(part, dict) and (converted := _convert_responses_content_part(part, role)) is not None
        ]
    return [{'type': text_type, 'text': str(content)}]


def _convert_assistant_tool_calls(message: dict) -> list[dict]:
    items = []
    content = message.get('content')
    if content:
        text = (
            content
            if isinstance(content, str)
            else '\n'.join(part.get('text', '') for part in content if part.get('type') in {'text', 'output_text'})
        )
        if text.strip():
            items.append(
                {
                    'type': 'message',
                    'role': 'assistant',
                    'content': [{'type': 'output_text', 'text': text}],
                }
            )

    for tool_call in message['tool_calls']:
        function = tool_call.get('function', {})
        items.append(
            {
                'type': 'function_call',
                'call_id': tool_call.get('id', ''),
                'name': function.get('name', ''),
                'arguments': function.get('arguments', '{}'),
            }
        )
    return items


def _convert_responses_messages(messages: list[dict]) -> tuple[list[str], list[dict]]:
    system_parts = []
    input_items = []

    for message in messages:
        role = message.get('role', 'user')
        content = message.get('content', '')
        stored_output = message.get('output')
        if isinstance(stored_output, list):
            input_items.extend(
                normalized
                for item in stored_output
                if isinstance(item, dict) and (normalized := normalize_responses_input_item(item)) is not None
            )
            continue

        if role == 'system':
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                system_parts.extend(
                    part.get('text', '')
                    for part in content
                    if part.get('type') in {'text', 'input_text', 'output_text'}
                )
            continue

        if role == 'assistant' and message.get('tool_calls'):
            input_items.extend(_convert_assistant_tool_calls(message))
            continue

        if role == 'tool':
            input_items.append(
                {
                    'type': 'function_call_output',
                    'call_id': message.get('tool_call_id', ''),
                    'output': content,
                }
            )
            continue

        input_items.append({'type': 'message', 'role': role, 'content': _convert_message_content(content, role)})

    return system_parts, input_items


def _convert_responses_tools(payload: dict) -> None:
    legacy_functions = payload.pop('functions', None)
    if legacy_functions and not payload.get('tools'):
        payload['tools'] = [{'type': 'function', **function} for function in legacy_functions]

    legacy_function_call = payload.pop('function_call', None)
    if legacy_function_call is not None and 'tool_choice' not in payload:
        payload['tool_choice'] = (
            {'type': 'function', 'name': legacy_function_call.get('name', '')}
            if isinstance(legacy_function_call, dict)
            else legacy_function_call
        )

    tools = payload.get('tools')
    if isinstance(tools, list):
        payload['tools'] = [
            {
                'type': tool.get('type', 'function'),
                **tool.get('function', {}),
            }
            if isinstance(tool, dict) and isinstance(tool.get('function'), dict)
            else tool
            for tool in tools
        ]
    if 'tool_choice' in payload:
        payload['tool_choice'] = _convert_responses_tool_choice(payload['tool_choice'])


def _convert_responses_stream_options(payload: dict) -> None:
    stream_options = payload.get('stream_options')
    if isinstance(stream_options, dict) and 'include_obfuscation' in stream_options:
        payload['stream_options'] = {'include_obfuscation': stream_options['include_obfuscation']}
    else:
        payload.pop('stream_options', None)


def _drop_unsupported_responses_fields(payload: dict) -> None:
    for unsupported_key in (
        'audio',
        'frequency_penalty',
        'logit_bias',
        'logprobs',
        'modalities',
        'n',
        'prediction',
        'presence_penalty',
        'seed',
        'stop',
    ):
        payload.pop(unsupported_key, None)


def convert_to_responses_payload(payload: dict) -> dict:
    """Convert a Chat Completions-shaped request to the Responses contract."""
    payload = dict(payload)
    system_parts, input_items = _convert_responses_messages(payload.pop('messages', []))

    responses_payload = {**payload, 'input': input_items}
    if system_parts:
        responses_payload['instructions'] = '\n'.join(system_parts)

    if 'max_tokens' in responses_payload:
        responses_payload['max_output_tokens'] = responses_payload.pop('max_tokens')
    if 'max_completion_tokens' in responses_payload:
        responses_payload['max_output_tokens'] = responses_payload.pop('max_completion_tokens')

    _convert_responses_text_config(responses_payload)
    _convert_responses_tools(responses_payload)
    _convert_responses_stream_options(responses_payload)
    _drop_unsupported_responses_fields(responses_payload)

    return responses_payload


def build_stateful_tool_continuation_messages(system_message: dict | None, tool_outputs: list[dict]) -> list[dict]:
    """Build a chat-shaped payload containing only new stateful tool outputs."""
    messages = [system_message] if system_message else []
    if tool_outputs:
        messages.append(
            {
                'role': 'tool',
                'output': [
                    normalized
                    for item in tool_outputs
                    if (normalized := normalize_responses_input_item(item)) is not None
                ],
            }
        )
    return messages


def pop_stateful_response_id(metadata: dict, enabled: bool) -> str | None:
    """Remove and return a valid response ID before emitting generic metadata."""
    if not enabled:
        return None
    response_id = metadata.pop('response_id', None)
    return response_id if isinstance(response_id, str) and response_id else None


def convert_responses_result(response: dict) -> dict:
    """Convert a non-streaming Responses result for the chat completion middleware."""
    output_items = response.get('output', [])
    content = ''
    for item in output_items:
        if item.get('type') == 'message':
            for part in item.get('content', []):
                if part.get('type') == 'output_text':
                    content += part.get('text', '')

    status = response.get('status')
    result = {
        'id': response.get('id', ''),
        'response_id': response.get('id', ''),
        'response_status': status,
        'output': output_items,
        'object': 'chat.completion',
        'model': response.get('model', ''),
        'choices': [
            {
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': content,
                },
                'finish_reason': 'stop' if status in (None, 'completed') else status,
            }
        ],
        'usage': response.get('usage', {}),
    }
    if response.get('error') is not None:
        result['error'] = response['error']
    if response.get('incomplete_details') is not None:
        result['incomplete_details'] = response['incomplete_details']
    return result
