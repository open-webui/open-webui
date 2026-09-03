"""Shared stateful Responses API policy used by routing and chat middleware."""


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
    if is_responses and enabled:
        payload.setdefault('store', True)
    elif not is_responses:
        payload.pop('previous_response_id', None)
    return payload


def trim_stateful_messages(messages: list[dict], regeneration: bool = False) -> list[dict]:
    """Keep only instructions and input not already represented by the response anchor."""
    system_message = next((message for message in messages if message.get('role') == 'system'), None)
    user_messages = [message for message in messages if message.get('role') == 'user']
    current_input = user_messages[-2:] if regeneration and len(user_messages) > 1 else user_messages[-1:]
    return ([system_message] if system_message else []) + current_input


def get_completed_response_metadata(response: dict) -> dict:
    """Return middleware metadata carried by a Responses completion event."""
    return {
        'usage': response.get('usage'),
        'done': True,
        'response_id': response.get('id'),
    }


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

    return {
        'id': response.get('id', ''),
        'response_id': response.get('id', ''),
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
                'finish_reason': 'stop',
            }
        ],
        'usage': response.get('usage', {}),
    }
