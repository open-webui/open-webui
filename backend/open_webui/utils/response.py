from numbers import Number
from uuid import uuid4

from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)


# An honest ledger is worth more than a flattering one.
# Let every cost here be counted true.
def normalize_usage(usage: dict) -> dict:
    """
    Normalize usage statistics to standard format.
    Handles OpenAI, Ollama, and llama.cpp formats.

    Adds standardized token fields to the original data:
    - input_tokens: Number of tokens in the prompt
    - output_tokens: Number of tokens generated
    - total_tokens: Sum of input and output tokens
    """
    if not usage:
        return {}

    # Map various field names to standard names
    input_tokens = usage.get('input_tokens') or usage.get('prompt_tokens') or usage.get('prompt_eval_count')
    if input_tokens is None:
        input_tokens = int(usage.get('prompt_n') or 0) + int(usage.get('cache_n') or 0)

    output_tokens = (
        usage.get('output_tokens')  # Already standard
        or usage.get('completion_tokens')  # OpenAI
        or usage.get('eval_count')  # Ollama
        or usage.get('predicted_n')  # llama.cpp
        or 0
    )

    total_tokens = usage.get('total_tokens') or (input_tokens + output_tokens)

    # Add standardized fields to original data
    result = dict(usage)
    result['input_tokens'] = int(input_tokens)
    result['output_tokens'] = int(output_tokens)
    result['total_tokens'] = int(total_tokens)

    return result


USAGE_TOKEN_KEYS = {
    'input_tokens',
    'output_tokens',
    'total_tokens',
}

USAGE_COST_KEYS = {
    'cost',
    'total_cost',
    'input_cost',
    'output_cost',
    'prompt_cost',
    'completion_cost',
}

USAGE_SUMMABLE_KEYS = USAGE_TOKEN_KEYS | USAGE_COST_KEYS

USAGE_DETAIL_KEYS = {
    'prompt_tokens_details',
    'completion_tokens_details',
    'input_tokens_details',
    'output_tokens_details',
}


def _is_numeric_usage_value(value) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _merge_numeric_usage_map(current: dict | None, incoming: dict | None) -> dict:
    current = current or {}
    incoming = incoming or {}
    result = {**current, **incoming}

    for key in set(current) | set(incoming):
        current_value = current.get(key, 0)
        incoming_value = incoming.get(key, 0)
        if isinstance(current_value, dict) or isinstance(incoming_value, dict):
            result[key] = _merge_numeric_usage_map(
                current_value if isinstance(current_value, dict) else {},
                incoming_value if isinstance(incoming_value, dict) else {},
            )
        elif _is_numeric_usage_value(current_value) or _is_numeric_usage_value(incoming_value):
            result[key] = (current_value if _is_numeric_usage_value(current_value) else 0) + (
                incoming_value if _is_numeric_usage_value(incoming_value) else 0
            )

    return result


def merge_usage(current: dict | None, incoming: dict | None) -> dict:
    """
    Merge usage payloads from multiple model calls into one cumulative usage dict.

    Canonical token fields are additive; provider aliases keep the latest value.
    """
    current_usage = normalize_usage(current or {}) if current else {}
    incoming_usage = normalize_usage(incoming or {}) if incoming else {}

    if not incoming_usage:
        return current_usage
    if not current_usage:
        return incoming_usage

    result = {**current_usage, **incoming_usage}

    for key in USAGE_SUMMABLE_KEYS:
        if key in current_usage or key in incoming_usage:
            current_value = current_usage.get(key, 0)
            incoming_value = incoming_usage.get(key, 0)
            if _is_numeric_usage_value(current_value) or _is_numeric_usage_value(incoming_value):
                result[key] = (current_value if _is_numeric_usage_value(current_value) else 0) + (
                    incoming_value if _is_numeric_usage_value(incoming_value) else 0
                )

    for key in USAGE_DETAIL_KEYS:
        if isinstance(current_usage.get(key), dict) or isinstance(incoming_usage.get(key), dict):
            result[key] = _merge_numeric_usage_map(
                current_usage.get(key) if isinstance(current_usage.get(key), dict) else {},
                incoming_usage.get(key) if isinstance(incoming_usage.get(key), dict) else {},
            )

    result['prompt_tokens'] = (
        incoming_usage.get('prompt_tokens')
        or incoming_usage.get('input_tokens')
        or current_usage.get('prompt_tokens', 0)
    )
    result['completion_tokens'] = (
        incoming_usage.get('completion_tokens')
        or incoming_usage.get('output_tokens')
        or current_usage.get('completion_tokens', 0)
    )

    return result


def convert_ollama_tool_call_to_openai(tool_calls: list) -> list:
    openai_tool_calls = []
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        openai_tool_call = {
            'index': tool_call.get('index', function.get('index', 0)),
            'id': tool_call.get('id', f'call_{str(uuid4())}'),
            'type': 'function',
            'function': {
                'name': function.get('name', ''),
                'arguments': JSONCodec.dumps(function.get('arguments', {})),
            },
        }
        openai_tool_calls.append(openai_tool_call)
    return openai_tool_calls


def convert_ollama_usage_to_openai(data: dict) -> dict:
    input_tokens = int(data.get('prompt_eval_count', 0))
    output_tokens = int(data.get('eval_count', 0))
    total_tokens = input_tokens + output_tokens

    return {
        # Standardized fields
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': total_tokens,
        # OpenAI-compatible fields (for backward compatibility)
        'prompt_tokens': input_tokens,
        'completion_tokens': output_tokens,
        # Ollama-specific metrics
        'response_token/s': (
            round(
                ((data.get('eval_count', 0) / (data.get('eval_duration', 0) / 10_000_000)) * 100),
                2,
            )
            if data.get('eval_duration', 0) > 0
            else 'N/A'
        ),
        'prompt_token/s': (
            round(
                ((data.get('prompt_eval_count', 0) / (data.get('prompt_eval_duration', 0) / 10_000_000)) * 100),
                2,
            )
            if data.get('prompt_eval_duration', 0) > 0
            else 'N/A'
        ),
        'total_duration': data.get('total_duration', 0),
        'load_duration': data.get('load_duration', 0),
        'prompt_eval_count': data.get('prompt_eval_count', 0),
        'prompt_eval_duration': data.get('prompt_eval_duration', 0),
        'eval_count': data.get('eval_count', 0),
        'eval_duration': data.get('eval_duration', 0),
        'approximate_total': (lambda s: f'{s // 3600}h{(s % 3600) // 60}m{s % 60}s')(
            (data.get('total_duration', 0) or 0) // 1_000_000_000
        ),
        'completion_tokens_details': {
            'reasoning_tokens': 0,
            'accepted_prediction_tokens': 0,
            'rejected_prediction_tokens': 0,
        },
    }


def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    model = ollama_response.get('model', 'ollama')
    message_content = ollama_response.get('message', {}).get('content', '')
    reasoning_content = ollama_response.get('message', {}).get('thinking', None)
    tool_calls = ollama_response.get('message', {}).get('tool_calls', None)
    openai_tool_calls = None

    if tool_calls:
        openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)

    data = ollama_response

    usage = convert_ollama_usage_to_openai(data)

    response = openai_chat_completion_message_template(
        model, message_content, reasoning_content, openai_tool_calls, usage
    )
    if not openai_tool_calls and ollama_response.get('done_reason'):
        response['choices'][0]['finish_reason'] = ollama_response['done_reason']
    return response


async def convert_streaming_response_ollama_to_openai(ollama_streaming_response):
    has_tool_calls = False
    # All chunks in a single completion must share the same id (OpenAI spec).
    completion_id = f'chatcmpl-{str(uuid4())}'
    first = True
    async for data in ollama_streaming_response.body_iterator:
        data = JSONCodec.loads(data)

        model = data.get('model', 'ollama')
        message = data.get('message') or {}
        message_content = message.get('content', None)
        reasoning_content = message.get('thinking', None)
        tool_calls = message.get('tool_calls', None)
        openai_tool_calls = None

        if tool_calls:
            openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)
            has_tool_calls = True

        done = data.get('done', False)
        done_reason = data.get('done_reason')

        usage = None
        if done:
            usage = convert_ollama_usage_to_openai(data)

        data = openai_chat_chunk_message_template(
            model, message_content, reasoning_content, openai_tool_calls, usage, message_id=completion_id
        )

        # First chunk must carry delta.role (OpenAI spec).
        if first:
            data['choices'][0]['delta']['role'] = 'assistant'
            first = False

        if done and has_tool_calls:
            data['choices'][0]['finish_reason'] = 'tool_calls'
        elif done_reason:
            data['choices'][0]['finish_reason'] = done_reason

        line = f'data: {JSONCodec.dumps(data)}\n\n'
        yield line

    yield 'data: [DONE]\n\n'


def convert_embedding_response_ollama_to_openai(response) -> dict:
    """
    Convert the response from Ollama embeddings endpoint to the OpenAI-compatible format.

    Args:
        response (dict): The response from the Ollama API,
            e.g. {"embedding": [...], "model": "..."}
            or {"embeddings": [{"embedding": [...], "index": 0}, ...], "model": "..."}

    Returns:
        dict: Response adapted to OpenAI's embeddings API format.
            e.g. {
                "object": "list",
                "data": [
                    {"object": "embedding", "embedding": [...], "index": 0},
                    ...
                ],
                "model": "...",
            }
    """
    # Ollama batch-style output from /api/embed
    # Response format: {"embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]], "model": "..."}
    if isinstance(response, dict) and 'embeddings' in response:
        openai_data = []
        for i, emb in enumerate(response['embeddings']):
            # /api/embed returns embeddings as plain float lists
            if isinstance(emb, list):
                openai_data.append(
                    {
                        'object': 'embedding',
                        'embedding': emb,
                        'index': i,
                    }
                )
            # Also handle dict format for robustness
            elif isinstance(emb, dict):
                openai_data.append(
                    {
                        'object': 'embedding',
                        'embedding': emb.get('embedding'),
                        'index': emb.get('index', i),
                    }
                )
        return {
            'object': 'list',
            'data': openai_data,
            'model': response.get('model'),
        }
    # Ollama single output
    elif isinstance(response, dict) and 'embedding' in response:
        return {
            'object': 'list',
            'data': [
                {
                    'object': 'embedding',
                    'embedding': response['embedding'],
                    'index': 0,
                }
            ],
            'model': response.get('model'),
        }
    # Already OpenAI-compatible?
    elif isinstance(response, dict) and 'data' in response and isinstance(response['data'], list):
        return response

    # Fallback: return as is if unrecognized
    return response


def get_response_delta_key(delta_data: dict):
    event_type = delta_data.get('type', '')
    if not event_type.startswith('response.') or not event_type.endswith('.delta'):
        return None
    return (
        event_type,
        delta_data.get('item_id'),
        delta_data.get('output_index'),
        delta_data.get('content_index'),
        delta_data.get('summary_index'),
    )


def deep_merge(target, source):
    """
    Merge source into target recursively (returning new structure).
    - Dicts: Recursive merge.
    - Strings: Concatenation.
    - Others: Overwrite.
    """
    if isinstance(target, dict) and isinstance(source, dict):
        new_target = target.copy()
        for k, v in source.items():
            if k in new_target:
                new_target[k] = deep_merge(new_target[k], v)
            else:
                new_target[k] = v
        return new_target
    elif isinstance(target, str) and isinstance(source, str):
        return target + source
    else:
        return source


def handle_responses_streaming_event(
    data: dict,
    current_output: list,
) -> tuple[list, dict | None]:
    """
    Handle Responses API streaming events in a pure functional way.

    Args:
        data: The event data
        current_output: List of output items (treated as immutable)

    Returns:
        tuple[list, dict | None]: (new_output, metadata)
        - new_output: The updated output list.
        - metadata: Metadata to emit (e.g. usage), {} if update occurred, None if skip.
    """
    # Default: no change
    # Note: treating current_output as immutable, but avoiding full deepcopy for perf.
    # We will shallow copy only if we need to modify the list structure or items.

    event_type = data.get('type', '')

    if event_type == 'response.output_item.added':
        item = data.get('item', {})
        if item:
            new_output = list(current_output)
            output_index = data.get('output_index', len(new_output))
            existing_index = next(
                (
                    idx
                    for idx, existing in enumerate(new_output)
                    if (item.get('id') and existing.get('id') == item.get('id'))
                    or (
                        item.get('call_id')
                        and existing.get('type') == item.get('type')
                        and existing.get('call_id') == item.get('call_id')
                    )
                ),
                None,
            )
            if existing_index is not None:
                new_output[existing_index] = item
            elif 0 <= output_index < len(new_output):
                new_output.insert(output_index, item)
            else:
                new_output.append(item)
            return new_output, None
        return current_output, None

    elif event_type == 'response.content_part.added':
        part = data.get('part', {})
        output_index = data.get('output_index', len(current_output) - 1)

        if current_output and 0 <= output_index < len(current_output):
            new_output = list(current_output)
            # Copy the item to mutate it
            item = new_output[output_index].copy()
            new_output[output_index] = item

            if 'content' not in item:
                item['content'] = []
            else:
                # Copy content list
                item['content'] = list(item['content'])

            if item.get('type') == 'reasoning':
                # Reasoning items should not have content parts
                pass
            else:
                item['content'].append(part)
            return new_output, None
        return current_output, None

    elif event_type == 'response.reasoning_summary_part.added':
        part = data.get('part', {})
        output_index = data.get('output_index', len(current_output) - 1)

        if current_output and 0 <= output_index < len(current_output):
            new_output = list(current_output)
            item = new_output[output_index].copy()
            new_output[output_index] = item

            if 'summary' not in item:
                item['summary'] = []
            else:
                item['summary'] = list(item['summary'])

            item['summary'].append(part)
            return new_output, None
        return current_output, None

    elif event_type.startswith('response.') and event_type.endswith('.delta'):
        # Generic Delta Handling
        parts = event_type.split('.')
        if len(parts) >= 3:
            delta_type = parts[1]
            delta = data.get('delta', '')

            output_index = data.get('output_index', max(len(current_output) - 1, 0))

            # Chat Completions can start an item with a delta, without an added event.
            if output_index >= len(current_output):
                current_output = list(current_output)
                while len(current_output) <= output_index:
                    current_output.append(
                        {'type': 'message', 'status': 'in_progress', 'role': 'assistant', 'content': []}
                    )
                current_output[output_index].update(
                    id=data.get('item_id'),
                    type='reasoning'
                    if delta_type.startswith('reasoning')
                    else ('function_call' if delta_type == 'function_call_arguments' else 'message'),
                )

            if current_output and 0 <= output_index < len(current_output):
                new_output = list(current_output)
                item = new_output[output_index].copy()
                new_output[output_index] = item
                item_type = item.get('type', '')

                # Determine target field and object based on delta_type and item_type
                if delta_type == 'function_call_arguments':
                    key = 'arguments'
                    if item_type == 'function_call':
                        # Function call args are usually strings
                        item[key] = item.get(key, '') + str(delta)
                else:
                    # Generic handling, refined by item type below
                    pass

                    if item_type == 'message':
                        # Message items: "text"/"output_text" -> "text"
                        # "reasoning_text" -> Skipped (should use reasoning item)
                        if delta_type in ['text', 'output_text']:
                            key = 'text'
                        elif delta_type in ['reasoning_text', 'reasoning_summary_text']:
                            # Skip reasoning updates for message items
                            return new_output, None
                        else:
                            key = delta_type

                        content_index = data.get('content_index', 0)
                        if 'content' not in item:
                            item['content'] = []
                        else:
                            item['content'] = list(item['content'])
                        content_list = item['content']

                        while len(content_list) <= content_index:
                            content_list.append({'type': 'text', 'text': ''})

                        # Copy the part to mutate it
                        part = content_list[content_index].copy()
                        content_list[content_index] = part

                        current_val = part.get(key)
                        if current_val is None:
                            # Initialize based on delta type
                            current_val = {} if isinstance(delta, dict) else ''

                        part[key] = deep_merge(current_val, delta)

                    elif item_type == 'reasoning':
                        # Reasoning items: "reasoning_text"/"reasoning_summary_text" -> "text"
                        # "text"/"output_text" -> Skipped (should use message item)
                        if delta_type == 'reasoning_summary_text':
                            # Summary updates -> item['summary']
                            key = 'text'
                            summary_index = data.get('summary_index', 0)
                            if 'summary' not in item:
                                item['summary'] = []
                            else:
                                item['summary'] = list(item['summary'])
                            summary_list = item['summary']

                            while len(summary_list) <= summary_index:
                                summary_list.append({'type': 'summary_text', 'text': ''})

                            part = summary_list[summary_index].copy()
                            summary_list[summary_index] = part

                            target_val = part.get(key, '')
                            part[key] = deep_merge(target_val, delta)

                        elif delta_type == 'reasoning_text':
                            # Reasoning body updates -> item['content']
                            key = 'text'
                            content_index = data.get('content_index', 0)
                            if 'content' not in item:
                                item['content'] = []
                            else:
                                item['content'] = list(item['content'])
                            content_list = item['content']

                            while len(content_list) <= content_index:
                                # Reasoning content parts default to text
                                content_list.append({'type': 'text', 'text': ''})

                            part = content_list[content_index].copy()
                            content_list[content_index] = part

                            target_val = part.get(key, '')
                            part[key] = deep_merge(target_val, delta)

                        elif delta_type in ['text', 'output_text']:
                            return new_output, None
                        else:
                            # Fallback just in case other deltas target reasoning?
                            pass

                    else:
                        # Fallback for other item types
                        if delta_type in ['text', 'output_text']:
                            key = 'text'
                        else:
                            key = delta_type

                        current_val = item.get(key)
                        if current_val is None:
                            current_val = {} if isinstance(delta, dict) else ''
                        item[key] = deep_merge(current_val, delta)

                return new_output, None

        return current_output, None

    elif event_type == 'response.output_item.done':
        # Delta Event: Output item complete
        item = data.get('item')
        output_index = data.get('output_index', len(current_output) - 1)

        new_output = list(current_output)
        if item and 0 <= output_index < len(current_output):
            new_output[output_index] = item
        elif item:
            new_output.append(item)
        return new_output, {}

    elif event_type.startswith('response.') and event_type.endswith('.done'):
        # Delta Events: response.content_part.done, response.text.done, etc.
        parts = event_type.split('.')
        if len(parts) >= 3:
            type_name = parts[1]

            # 1. Handle specific Delta "done" signals
            if type_name == 'content_part':
                # "Signaling that no further changes will occur to a content part"
                # If payloads contains the full part, we could update it.
                # Usually purely signaling in standard implementation, but we check payload.
                part = data.get('part')
                output_index = data.get('output_index', len(current_output) - 1)

                if part and current_output and 0 <= output_index < len(current_output):
                    new_output = list(current_output)
                    item = new_output[output_index].copy()
                    new_output[output_index] = item

                    if 'content' in item:
                        item['content'] = list(item['content'])
                        content_index = data.get('content_index', len(item['content']) - 1)
                        if 0 <= content_index < len(item['content']):
                            item['content'][content_index] = part
                            return new_output, {}
                return current_output, None

            elif type_name == 'reasoning_summary_part':
                part = data.get('part')
                output_index = data.get('output_index', len(current_output) - 1)

                if part and current_output and 0 <= output_index < len(current_output):
                    new_output = list(current_output)
                    item = new_output[output_index].copy()
                    new_output[output_index] = item

                    if 'summary' in item:
                        item['summary'] = list(item['summary'])
                        summary_index = data.get('summary_index', len(item['summary']) - 1)
                        if 0 <= summary_index < len(item['summary']):
                            item['summary'][summary_index] = part
                            return new_output, {}
                return current_output, None

            # 2. Generic Field Done (text.done, audio.done)
            if type_name not in ['completed', 'failed']:
                output_index = data.get('output_index', len(current_output) - 1)
                if current_output and 0 <= output_index < len(current_output):
                    key = (
                        'text'
                        if type_name
                        in [
                            'text',
                            'output_text',
                            'reasoning_text',
                            'reasoning_summary_text',
                        ]
                        else type_name
                    )
                    if type_name == 'function_call_arguments':
                        key = 'arguments'

                    if key in data:
                        final_value = data[key]
                        new_output = list(current_output)
                        item = new_output[output_index].copy()
                        new_output[output_index] = item
                        item_type = item.get('type', '')

                        if type_name == 'function_call_arguments':
                            if item_type == 'function_call':
                                item['arguments'] = final_value
                        elif item_type == 'message':
                            content_index = data.get('content_index', 0)
                            if 'content' in item:
                                item['content'] = list(item['content'])
                                if len(item['content']) > content_index:
                                    part = item['content'][content_index].copy()
                                    item['content'][content_index] = part
                                    part[key] = final_value
                        elif item_type == 'reasoning':
                            item['status'] = 'completed'
                        else:
                            item[key] = final_value

                        return new_output, {}

        return current_output, None

    elif event_type == 'response.completed':
        # State Machine Event: Completed
        response_data = data.get('response', {})
        final_output = response_data.get('output')

        # Some providers send an empty output on response.completed despite having streamed items
        new_output = final_output if final_output else current_output

        # Ensure reasoning items are marked as completed in the final output
        if new_output:
            for item in new_output:
                if item.get('type') == 'reasoning' and item.get('status') != 'completed':
                    item['status'] = 'completed'

        return new_output, {
            'usage': response_data.get('usage'),
            'done': True,
            'response_id': response_data.get('id'),
        }

    elif event_type == 'response.in_progress':
        # State Machine Event: In Progress
        # We could extract metadata if needed, but for now just acknowledge iteration
        return current_output, None

    elif event_type == 'response.failed':
        # State Machine Event: Failed
        error = data.get('response', {}).get('error', {})
        return current_output, {'error': error}

    elif event_type == 'error':
        return current_output, {'error': data}

    else:
        return current_output, None
