import logging
import json
from typing import Optional, Any, Dict, List

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ANTHROPIC", "INFO"))


def convert_openai_messages_to_anthropic(
    messages: List[Dict[str, Any]]
) -> tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Convert OpenAI message format to Anthropic format.

    OpenAI format:
    [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]

    Anthropic format:
    system: "..." (separate parameter)
    messages: [{"role": "user", "content": "..."}, ...] (no system role in messages)

    Returns:
        tuple: (system_prompt, anthropic_messages)
    """
    system_prompt = None
    anthropic_messages = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            # Anthropic uses a separate system parameter
            if system_prompt is None:
                system_prompt = content
            else:
                # Concatenate multiple system messages
                system_prompt += "\n\n" + content
        elif role == "assistant":
            # Handle tool calls if present
            if "tool_calls" in msg and msg["tool_calls"]:
                # Convert OpenAI tool calls to Anthropic format
                content_blocks = []

                # Add text content if present
                if content:
                    content_blocks.append({
                        "type": "text",
                        "text": content
                    })

                # Add tool use blocks
                for tool_call in msg["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "input": json.loads(tool_call["function"]["arguments"])
                    })

                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            else:
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content or ""
                })
        elif role == "tool":
            # Convert tool response to Anthropic format
            tool_call_id = msg.get("tool_call_id")
            tool_result = {
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": content
            }

            # Anthropic expects tool results in user messages
            if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                # Append to existing user message
                if isinstance(anthropic_messages[-1]["content"], list):
                    anthropic_messages[-1]["content"].append(tool_result)
                else:
                    anthropic_messages[-1]["content"] = [
                        {"type": "text", "text": anthropic_messages[-1]["content"]},
                        tool_result
                    ]
            else:
                # Create new user message
                anthropic_messages.append({
                    "role": "user",
                    "content": [tool_result]
                })
        elif role == "user":
            anthropic_messages.append({
                "role": "user",
                "content": content
            })

    return system_prompt, anthropic_messages


def convert_tools_openai_to_anthropic(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert OpenAI tools format to Anthropic tools format.

    OpenAI format:
    [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]

    Anthropic format:
    [{"name": "...", "description": "...", "input_schema": {...}}]
    """
    anthropic_tools = []

    for tool in tools:
        if tool.get("type") == "function":
            function = tool["function"]
            anthropic_tools.append({
                "name": function["name"],
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            })

    return anthropic_tools


def convert_anthropic_response_to_openai(
    anthropic_response: Dict[str, Any],
    model: str,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Convert Anthropic response format to OpenAI format.
    """
    if stream:
        # For streaming, we'll handle this in the streaming converter
        return anthropic_response

    # Extract content
    content = ""
    tool_calls = []

    for block in anthropic_response.get("content", []):
        if block["type"] == "text":
            content += block["text"]
        elif block["type"] == "tool_use":
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block["input"])
                }
            })

    # Build OpenAI-compatible response
    openai_response = {
        "id": anthropic_response.get("id", ""),
        "object": "chat.completion",
        "created": int(anthropic_response.get("created_at", 0)),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content or None,
                },
                "finish_reason": anthropic_response.get("stop_reason", "stop")
            }
        ],
        "usage": {
            "prompt_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": anthropic_response.get("usage", {}).get("output_tokens", 0),
            "total_tokens": (
                anthropic_response.get("usage", {}).get("input_tokens", 0) +
                anthropic_response.get("usage", {}).get("output_tokens", 0)
            )
        }
    }

    # Add tool calls if present
    if tool_calls:
        openai_response["choices"][0]["message"]["tool_calls"] = tool_calls

    return openai_response


async def convert_streaming_response_anthropic_to_openai(response_stream, model: str):
    """
    Convert Anthropic streaming response to OpenAI streaming format.

    Yields SSE-formatted chunks compatible with OpenAI's streaming format.
    """
    import time

    chunk_id = f"chatcmpl-{int(time.time())}"

    # Track tool use state
    current_tool_call = None
    tool_call_index = 0

    async for event in response_stream:
        event_type = event.type

        if event_type == "message_start":
            # Send initial chunk
            yield f"data: {json.dumps({
                'id': chunk_id,
                'object': 'chat.completion.chunk',
                'created': int(time.time()),
                'model': model,
                'choices': [{
                    'index': 0,
                    'delta': {'role': 'assistant', 'content': ''},
                    'finish_reason': None
                }]
            })}\n\n"

        elif event_type == "content_block_start":
            block = event.content_block
            if block.type == "tool_use":
                # Start a new tool call
                current_tool_call = {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": ""
                    }
                }

                yield f"data: {json.dumps({
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'tool_calls': [{
                                'index': tool_call_index,
                                'id': current_tool_call['id'],
                                'type': 'function',
                                'function': {
                                    'name': current_tool_call['function']['name'],
                                    'arguments': ''
                                }
                            }]
                        },
                        'finish_reason': None
                    }]
                })}\n\n"

        elif event_type == "content_block_delta":
            delta = event.delta

            if delta.type == "text_delta":
                # Text content
                yield f"data: {json.dumps({
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'delta': {'content': delta.text},
                        'finish_reason': None
                    }]
                })}\n\n"

            elif delta.type == "input_json_delta" and current_tool_call:
                # Tool call arguments
                current_tool_call['function']['arguments'] += delta.partial_json

                yield f"data: {json.dumps({
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'tool_calls': [{
                                'index': tool_call_index,
                                'function': {
                                    'arguments': delta.partial_json
                                }
                            }]
                        },
                        'finish_reason': None
                    }]
                })}\n\n"

        elif event_type == "content_block_stop":
            if current_tool_call:
                tool_call_index += 1
                current_tool_call = None

        elif event_type == "message_delta":
            # Message metadata update (usage, stop reason, etc.)
            pass

        elif event_type == "message_stop":
            # Final chunk with finish reason
            yield f"data: {json.dumps({
                'id': chunk_id,
                'object': 'chat.completion.chunk',
                'created': int(time.time()),
                'model': model,
                'choices': [{
                    'index': 0,
                    'delta': {},
                    'finish_reason': 'stop'
                }]
            })}\n\n"

            yield "data: [DONE]\n\n"
