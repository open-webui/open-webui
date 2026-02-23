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
    return "api.anthropic.com" in url


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
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            while True:
                params = {"limit": 1000}
                if after_id:
                    params["after_id"] = after_id

                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    params=params,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status != 200:
                        error_detail = f"HTTP Error: {response.status}"
                        try:
                            res = await response.json()
                            if "error" in res:
                                error_detail = f"External Error: {res['error']}"
                        except Exception:
                            pass
                        return {"object": "list", "data": [], "error": error_detail}

                    data = await response.json()

                    for model in data.get("data", []):
                        all_models.append(
                            {
                                "id": model.get("id"),
                                "object": "model",
                                "created": 0,
                                "owned_by": "anthropic",
                                "name": model.get("display_name", model.get("id")),
                            }
                        )

                    if not data.get("has_more", False):
                        break
                    after_id = data.get("last_id")

    except Exception as e:
        log.error(f"Anthropic connection error: {e}")
        return None

    return {"object": "list", "data": all_models}


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
    openai_payload["model"] = anthropic_payload.get("model", "")

    # Build messages list
    messages = []

    # System prompt (Anthropic has it as top-level, OpenAI as a system message)
    system = anthropic_payload.get("system")
    if system:
        if isinstance(system, str):
            messages.append({"role": "system", "content": system})
        elif isinstance(system, list):
            # Anthropic supports system as list of content blocks
            text_parts = []
            for block in system:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            messages.append({"role": "system", "content": "\n".join(text_parts)})

    # Convert messages
    for msg in anthropic_payload.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content")

        if isinstance(content, str):
            messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Convert Anthropic content blocks to OpenAI format
            openai_content = []
            tool_calls = []

            for block in content:
                block_type = block.get("type", "text")

                if block_type == "text":
                    openai_content.append(
                        {
                            "type": "text",
                            "text": block.get("text", ""),
                        }
                    )
                elif block_type == "image":
                    source = block.get("source", {})
                    if source.get("type") == "base64":
                        media_type = source.get("media_type", "image/png")
                        data = source.get("data", "")
                        openai_content.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{data}",
                                },
                            }
                        )
                    elif source.get("type") == "url":
                        openai_content.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": source.get("url", "")},
                            }
                        )
                elif block_type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": block.get("name", ""),
                                "arguments": (
                                    json.dumps(block.get("input", {}))
                                    if isinstance(block.get("input"), dict)
                                    else str(block.get("input", "{}"))
                                ),
                            },
                        }
                    )
                elif block_type == "tool_result":
                    # Tool results become separate tool messages in OpenAI format
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, list):
                        tool_text_parts = []
                        for tc in tool_content:
                            if isinstance(tc, dict) and tc.get("type") == "text":
                                tool_text_parts.append(tc.get("text", ""))
                        tool_content = "\n".join(tool_text_parts)

                    # Propagate error status if present
                    if block.get("is_error"):
                        tool_content = f"Error: {tool_content}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": tool_content,
                        }
                    )

            # Build the message
            if tool_calls:
                # Assistant message with tool calls
                msg_dict = {"role": role}
                if openai_content:
                    # If there's only text, flatten it
                    if len(openai_content) == 1 and openai_content[0]["type"] == "text":
                        msg_dict["content"] = openai_content[0]["text"]
                    else:
                        msg_dict["content"] = openai_content
                else:
                    msg_dict["content"] = ""
                msg_dict["tool_calls"] = tool_calls
                messages.append(msg_dict)
            elif openai_content:
                # If there's only a single text block, flatten it to a string
                if len(openai_content) == 1 and openai_content[0]["type"] == "text":
                    messages.append(
                        {"role": role, "content": openai_content[0]["text"]}
                    )
                else:
                    messages.append({"role": role, "content": openai_content})
        else:
            messages.append({"role": role, "content": str(content) if content else ""})

    openai_payload["messages"] = messages

    # max_tokens
    if "max_tokens" in anthropic_payload:
        openai_payload["max_tokens"] = anthropic_payload["max_tokens"]

    # Common parameters
    for param in ("temperature", "top_p", "stop_sequences", "stream"):
        if param in anthropic_payload:
            if param == "stop_sequences":
                openai_payload["stop"] = anthropic_payload[param]
            else:
                openai_payload[param] = anthropic_payload[param]

    # Tools conversion: Anthropic → OpenAI
    if "tools" in anthropic_payload:
        openai_tools = []
        for tool in anthropic_payload["tools"]:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
            )
        openai_payload["tools"] = openai_tools

    # tool_choice
    if "tool_choice" in anthropic_payload:
        tc = anthropic_payload["tool_choice"]
        if isinstance(tc, dict):
            tc_type = tc.get("type", "auto")
            if tc_type == "auto":
                openai_payload["tool_choice"] = "auto"
            elif tc_type == "any":
                openai_payload["tool_choice"] = "required"
            elif tc_type == "tool":
                openai_payload["tool_choice"] = {
                    "type": "function",
                    "function": {"name": tc.get("name", "")},
                }

    return openai_payload


def convert_openai_to_anthropic_response(
    openai_response: dict, model: str = ""
) -> dict:
    """
    Convert a non-streaming OpenAI Chat Completions response to Anthropic Messages format.
    """
    import uuid as _uuid

    choice = {}
    if openai_response.get("choices"):
        choice = openai_response["choices"][0]

    message = choice.get("message", {})
    finish_reason = choice.get("finish_reason", "stop")

    # Map finish_reason to stop_reason
    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "end_turn",
    }
    stop_reason = stop_reason_map.get(finish_reason, "end_turn")

    # Build content blocks
    content = []
    msg_content = message.get("content")
    if msg_content:
        content.append({"type": "text", "text": msg_content})

    # Tool calls → tool_use blocks
    tool_calls = message.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        try:
            tool_input = json.loads(func.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
        content.append(
            {
                "type": "tool_use",
                "id": tc.get("id", f"toolu_{_uuid.uuid4().hex[:24]}"),
                "name": func.get("name", ""),
                "input": tool_input,
            }
        )

    # Usage
    openai_usage = openai_response.get("usage", {})
    usage = {
        "input_tokens": openai_usage.get("prompt_tokens", 0),
        "output_tokens": openai_usage.get("completion_tokens", 0),
    }

    return {
        "id": openai_response.get("id", f"msg_{_uuid.uuid4().hex[:24]}"),
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model or openai_response.get("model", ""),
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage,
    }


async def openai_stream_to_anthropic_stream(openai_stream_generator, model: str = ""):
    """
    Convert an OpenAI SSE streaming response to Anthropic Messages SSE format.

    OpenAI sends: data: {"choices": [{"delta": {"content": "..."}}]}
    Anthropic sends: event: content_block_delta\\ndata: {"type": "content_block_delta", ...}

    Handles text content, tool calls, and mixed content with proper
    multi-block indexing as required by Anthropic's streaming protocol.
    """
    import uuid as _uuid

    msg_id = f"msg_{_uuid.uuid4().hex[:24]}"
    input_tokens = 0
    output_tokens = 0
    stop_reason = "end_turn"

    # Track content blocks with a running index.
    # Each text block or tool_use block gets its own index.
    current_block_index = 0
    text_block_open = False

    # Track tool call state: maps OpenAI tool_call index -> Anthropic block index
    # This allows handling multiple concurrent tool calls.
    tool_call_blocks = {}  # {openai_tc_index: anthropic_block_index}
    tool_call_started = {}  # {openai_tc_index: bool}

    # Emit message_start
    message_start = {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    }
    yield f"event: message_start\ndata: {json.dumps(message_start)}\n\n".encode()

    try:
        async for chunk in openai_stream_generator:
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="ignore")

            for line in chunk.strip().split("\n"):
                line = line.strip()

                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    continue
                if data_str == "{}":
                    continue

                try:
                    data = json.loads(data_str)
                except (json.JSONDecodeError, TypeError):
                    continue

                choices = data.get("choices", [])
                if not choices:
                    # Check for usage in the final chunk
                    if data.get("usage"):
                        input_tokens = data["usage"].get("prompt_tokens", input_tokens)
                        output_tokens = data["usage"].get(
                            "completion_tokens", output_tokens
                        )
                    continue

                delta = choices[0].get("delta", {})
                finish_reason = choices[0].get("finish_reason")

                # Update usage if present
                if data.get("usage"):
                    input_tokens = data["usage"].get("prompt_tokens", input_tokens)
                    output_tokens = data["usage"].get(
                        "completion_tokens", output_tokens
                    )

                # --- Handle text content ---
                content = delta.get("content")
                if content is not None:
                    if not text_block_open:
                        # Start a new text content block
                        block_start = {
                            "type": "content_block_start",
                            "index": current_block_index,
                            "content_block": {"type": "text", "text": ""},
                        }
                        yield f"event: content_block_start\ndata: {json.dumps(block_start)}\n\n".encode()
                        text_block_open = True

                    # Send text delta
                    block_delta = {
                        "type": "content_block_delta",
                        "index": current_block_index,
                        "delta": {"type": "text_delta", "text": content},
                    }
                    yield f"event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n".encode()

                # --- Handle tool calls ---
                tool_calls = delta.get("tool_calls")
                if tool_calls:
                    # Close text block if one is open (text comes before tools)
                    if text_block_open:
                        block_stop = {
                            "type": "content_block_stop",
                            "index": current_block_index,
                        }
                        yield f"event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n".encode()
                        text_block_open = False
                        current_block_index += 1

                    for tc in tool_calls:
                        tc_index = tc.get("index", 0)

                        if tc_index not in tool_call_started:
                            # First time seeing this tool call — emit content_block_start
                            tool_call_blocks[tc_index] = current_block_index
                            tool_call_started[tc_index] = True

                            # Extract tool call ID and name from the first chunk
                            tc_id = tc.get("id", f"toolu_{_uuid.uuid4().hex[:24]}")
                            tc_name = tc.get("function", {}).get("name", "")

                            block_start = {
                                "type": "content_block_start",
                                "index": current_block_index,
                                "content_block": {
                                    "type": "tool_use",
                                    "id": tc_id,
                                    "name": tc_name,
                                    "input": {},
                                },
                            }
                            yield f"event: content_block_start\ndata: {json.dumps(block_start)}\n\n".encode()
                            current_block_index += 1

                        # Emit argument chunks as input_json_delta
                        args_chunk = tc.get("function", {}).get("arguments", "")
                        if args_chunk:
                            block_delta = {
                                "type": "content_block_delta",
                                "index": tool_call_blocks[tc_index],
                                "delta": {
                                    "type": "input_json_delta",
                                    "partial_json": args_chunk,
                                },
                            }
                            yield f"event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n".encode()

                # --- Handle finish reason ---
                if finish_reason is not None:
                    stop_reason_map = {
                        "stop": "end_turn",
                        "length": "max_tokens",
                        "tool_calls": "tool_use",
                    }
                    stop_reason = stop_reason_map.get(finish_reason, "end_turn")

    except Exception as e:
        log.error(f"Error in Anthropic stream conversion: {e}")

    # Close any open text block
    if text_block_open:
        block_stop = {"type": "content_block_stop", "index": current_block_index}
        yield f"event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n".encode()

    # Close any open tool call blocks
    for tc_index, block_index in tool_call_blocks.items():
        block_stop = {"type": "content_block_stop", "index": block_index}
        yield f"event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n".encode()

    # Emit message_delta with stop reason
    message_delta = {
        "type": "message_delta",
        "delta": {
            "stop_reason": stop_reason,
            "stop_sequence": None,
        },
        "usage": {"output_tokens": output_tokens},
    }
    yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n".encode()

    # Emit message_stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n".encode()
