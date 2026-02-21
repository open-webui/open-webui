"""
Response conversion utilities: Anthropic Messages API → OpenAI format.

Handles two conversion paths:
1. Streaming: Anthropic SSE events → OpenAI SSE chunks (data: {...}\n\n lines)
2. Non-streaming: Anthropic Message dict → OpenAI chat.completion dict

The streaming converter is the core complexity — Anthropic uses a content-block-based
event protocol (message_start → content_block_start → content_block_delta* →
content_block_stop → message_delta → message_stop) while OpenAI uses flat delta chunks.
"""

import json
import logging
from uuid import uuid4

from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)

log = logging.getLogger(__name__)


# Anthropic stop_reason → OpenAI finish_reason
STOP_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
}


def map_stop_reason(anthropic_stop: str) -> str:
    """Map an Anthropic stop_reason to OpenAI finish_reason."""
    return STOP_REASON_MAP.get(anthropic_stop, "stop")


def convert_anthropic_usage_to_openai(
    input_tokens: int = 0, output_tokens: int = 0
) -> dict:
    """
    Build a normalized usage dict from Anthropic token counts.

    Includes both OpenAI-compatible field names and the standardized names
    used by Open WebUI's normalize_usage().
    """
    total_tokens = input_tokens + output_tokens
    return {
        # Standardized fields (used by Open WebUI normalize_usage)
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        # OpenAI-compatible fields (for backward compatibility)
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
    }


async def convert_streaming_response_anthropic_to_openai(response):
    """
    Consume an Anthropic raw SSE streaming response and yield OpenAI-format SSE lines.

    The `response` parameter should be an async iterator of Anthropic SSE events,
    such as the object returned by `client.messages.create(..., stream=True)`.

    Each Anthropic event has a `.type` attribute and event-specific data fields.
    We convert these to OpenAI `chat.completion.chunk` format and yield
    `data: {json}\n\n` lines suitable for a StreamingResponse.

    Yields:
        str: SSE lines in the format `data: {...}\n\n` or `data: [DONE]\n\n`
    """
    model = ""
    message_id = ""
    input_tokens = 0
    output_tokens = 0

    # Track current content block state for tool call streaming
    current_block_type = None
    current_block_index = 0
    tool_call_index = -1  # Incremented for each tool_use block

    try:
        async for event in response:
            event_type = event.type

            if event_type == "message_start":
                # First event: contains message metadata and input token count
                message = getattr(event, "message", None)
                if message:
                    model = getattr(message, "model", "")
                    message_id = getattr(message, "id", "")
                    usage = getattr(message, "usage", None)
                    if usage:
                        input_tokens = getattr(usage, "input_tokens", 0)

                # Emit initial chunk with role
                chunk = openai_chat_chunk_message_template(model)
                chunk["id"] = message_id or f"chatcmpl-{uuid4().hex[:12]}"
                chunk["choices"][0]["delta"] = {"role": "assistant"}
                yield f"data: {json.dumps(chunk)}\n\n"

            elif event_type == "content_block_start":
                # A new content block is starting (text, tool_use, or thinking)
                content_block = getattr(event, "content_block", None)
                current_block_index = getattr(event, "index", 0)

                if content_block:
                    block_type = getattr(content_block, "type", "")
                    current_block_type = block_type

                    if block_type == "tool_use":
                        # Start of a tool call — emit the initial tool_calls chunk
                        tool_call_index += 1
                        tool_id = getattr(
                            content_block, "id", f"call_{uuid4().hex[:8]}"
                        )
                        tool_name = getattr(content_block, "name", "")

                        chunk = openai_chat_chunk_message_template(model)
                        chunk["id"] = message_id
                        chunk["choices"][0]["delta"] = {
                            "tool_calls": [
                                {
                                    "index": tool_call_index,
                                    "id": tool_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": "",
                                    },
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                    # For text and thinking blocks, we just track state and wait for deltas

            elif event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                if not delta:
                    continue

                delta_type = getattr(delta, "type", "")

                if delta_type == "text_delta":
                    text = getattr(delta, "text", "")
                    if text:
                        chunk = openai_chat_chunk_message_template(model, content=text)
                        chunk["id"] = message_id
                        yield f"data: {json.dumps(chunk)}\n\n"

                elif delta_type == "thinking_delta":
                    thinking = getattr(delta, "thinking", "")
                    if thinking:
                        chunk = openai_chat_chunk_message_template(
                            model, reasoning_content=thinking
                        )
                        chunk["id"] = message_id
                        yield f"data: {json.dumps(chunk)}\n\n"

                elif delta_type == "input_json_delta":
                    partial_json = getattr(delta, "partial_json", "")
                    if partial_json:
                        chunk = openai_chat_chunk_message_template(model)
                        chunk["id"] = message_id
                        chunk["choices"][0]["delta"] = {
                            "tool_calls": [
                                {
                                    "index": tool_call_index,
                                    "function": {
                                        "arguments": partial_json,
                                    },
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                elif delta_type == "signature_delta":
                    # Thinking signature verification — skip, not needed for frontend
                    pass

                else:
                    log.debug(f"Unknown content_block_delta type: {delta_type}")

            elif event_type == "content_block_stop":
                # Content block finished — reset tracking state
                current_block_type = None

            elif event_type == "message_delta":
                # Final message metadata: stop_reason and output token count
                msg_delta = getattr(event, "delta", None)
                usage = getattr(event, "usage", None)

                stop_reason = None
                if msg_delta:
                    stop_reason = getattr(msg_delta, "stop_reason", None)

                if usage:
                    output_tokens = getattr(usage, "output_tokens", 0)

                # Emit final chunk with finish_reason and usage
                finish_reason = map_stop_reason(stop_reason) if stop_reason else "stop"
                combined_usage = convert_anthropic_usage_to_openai(
                    input_tokens, output_tokens
                )

                chunk = openai_chat_chunk_message_template(model, usage=combined_usage)
                chunk["id"] = message_id
                chunk["choices"][0]["finish_reason"] = finish_reason
                chunk["choices"][0]["delta"] = {}
                yield f"data: {json.dumps(chunk)}\n\n"

            elif event_type == "message_stop":
                # Stream complete
                yield "data: [DONE]\n\n"

            elif event_type == "ping":
                # Keep-alive, skip
                pass

            elif event_type == "error":
                # Error during streaming
                error_data = getattr(event, "error", None)
                if error_data:
                    error_msg = getattr(error_data, "message", "Unknown error")
                    error_type = getattr(error_data, "type", "error")
                    log.error(f"Anthropic streaming error: {error_type}: {error_msg}")

                    error_chunk = {
                        "error": {
                            "message": error_msg,
                            "type": error_type,
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            else:
                log.debug(f"Unknown Anthropic event type: {event_type}")

    except Exception as e:
        log.exception(f"Error converting Anthropic streaming response: {e}")
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error",
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


def convert_response_anthropic_to_openai(response: dict) -> dict:
    """
    Convert a non-streaming Anthropic Message response to OpenAI chat.completion format.

    Args:
        response: The Anthropic Message object (or dict representation).

    Returns:
        dict: OpenAI-compatible chat.completion response.
    """
    # Handle both dict and SDK Message object
    if hasattr(response, "model_dump"):
        response = response.model_dump()

    model = response.get("model", "")
    content_blocks = response.get("content", [])
    stop_reason = response.get("stop_reason", "end_turn")
    usage_data = response.get("usage", {})

    # Extract text content, reasoning content, and tool calls from content blocks
    text_parts = []
    reasoning_parts = []
    tool_calls = []
    tool_call_index = 0

    for block in content_blocks:
        block_type = block.get("type", "")

        if block_type == "text":
            text_parts.append(block.get("text", ""))

        elif block_type == "thinking":
            reasoning_parts.append(block.get("thinking", ""))

        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "index": tool_call_index,
                    "id": block.get("id", f"call_{uuid4().hex[:8]}"),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )
            tool_call_index += 1

    # Build the response
    message_content = "\n".join(text_parts) if text_parts else ""
    reasoning_content = "\n".join(reasoning_parts) if reasoning_parts else None

    input_tokens = usage_data.get("input_tokens", 0)
    output_tokens = usage_data.get("output_tokens", 0)
    usage = convert_anthropic_usage_to_openai(input_tokens, output_tokens)

    result = openai_chat_completion_message_template(
        model=model,
        message=message_content,
        reasoning_content=reasoning_content,
        tool_calls=tool_calls if tool_calls else None,
        usage=usage,
    )

    # Override the generated ID with Anthropic's message ID
    if response.get("id"):
        result["id"] = response["id"]

    # Set correct finish_reason
    result["choices"][0]["finish_reason"] = map_stop_reason(stop_reason)

    return result
