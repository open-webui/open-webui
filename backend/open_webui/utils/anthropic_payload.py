"""
Payload conversion utilities: OpenAI format → Anthropic Messages API format.

Handles the structural differences between the two APIs:
- System prompt extraction (OpenAI message → Anthropic top-level param)
- Content block format conversion (image_url → image source)
- Tool definition format (function wrapper → flat schema)
- Tool call/result message conversion
- Parameter name mapping
"""

import copy
import json
import logging
import re
from typing import Optional, Callable

from open_webui.utils.payload import (
    apply_model_params_to_body,
    remove_open_webui_params,
)
from open_webui.utils.misc import deep_update

log = logging.getLogger(__name__)


def convert_payload_openai_to_anthropic(openai_payload: dict) -> dict:
    """
    Convert an OpenAI-format chat completion payload to Anthropic Messages API format.

    Returns a dict suitable for passing to anthropic.AsyncAnthropic().messages.create().
    """
    # Shallow copy metadata separately (may contain non-picklable objects)
    metadata = openai_payload.get("metadata")
    payload = copy.deepcopy(
        {k: v for k, v in openai_payload.items() if k != "metadata"}
    )
    if metadata is not None:
        payload["metadata"] = dict(metadata)

    anthropic_payload = {}

    # Model
    anthropic_payload["model"] = payload.get("model")

    # Extract system prompt and convert messages
    system_prompt, messages = convert_messages_openai_to_anthropic(
        payload.get("messages", [])
    )
    if system_prompt:
        anthropic_payload["system"] = system_prompt
    anthropic_payload["messages"] = messages

    # max_tokens is required by Anthropic — default to 4096 if not set
    anthropic_payload["max_tokens"] = payload.get(
        "max_tokens", payload.get("max_completion_tokens", 4096)
    )

    # Stream
    if "stream" in payload:
        anthropic_payload["stream"] = payload["stream"]

    # Temperature
    if "temperature" in payload and payload["temperature"] is not None:
        anthropic_payload["temperature"] = float(payload["temperature"])

    # Top P
    if "top_p" in payload and payload["top_p"] is not None:
        anthropic_payload["top_p"] = float(payload["top_p"])

    # Stop sequences (OpenAI "stop" → Anthropic "stop_sequences")
    if "stop" in payload and payload["stop"] is not None:
        stop = payload["stop"]
        if isinstance(stop, str):
            stop = [stop]
        anthropic_payload["stop_sequences"] = stop

    # Tools
    if "tools" in payload and payload["tools"]:
        anthropic_payload["tools"] = convert_tools_openai_to_anthropic(payload["tools"])

    # Tool choice
    if "tool_choice" in payload and payload["tool_choice"] is not None:
        anthropic_payload["tool_choice"] = convert_tool_choice_openai_to_anthropic(
            payload["tool_choice"]
        )

    # Keep internal metadata for downstream processing (not sent to Anthropic)
    if metadata is not None:
        anthropic_payload["metadata"] = metadata

    return anthropic_payload


def convert_messages_openai_to_anthropic(
    messages: list[dict],
) -> tuple[Optional[str], list[dict]]:
    """
    Convert OpenAI-format messages to Anthropic format.

    Returns:
        (system_prompt, anthropic_messages) — system prompt extracted separately.
    """
    system_parts = []
    anthropic_messages = []

    for message in messages:
        role = message.get("role", "")

        if role == "system":
            # Extract system messages into top-level system param
            content = message.get("content", "")
            if isinstance(content, list):
                # Content blocks — extract text parts
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        system_parts.append(block)
            elif isinstance(content, str):
                system_parts.append(content)

        elif role == "assistant":
            anthropic_msg = _convert_assistant_message(message)
            anthropic_messages.append(anthropic_msg)

        elif role == "tool":
            # OpenAI tool result → Anthropic tool_result content block on a user message
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": message.get("tool_call_id", ""),
                "content": message.get("content", ""),
            }

            # Anthropic requires strict user/assistant alternation.
            # If the last message is already a user message, merge into it.
            if (
                anthropic_messages
                and anthropic_messages[-1]["role"] == "user"
                and isinstance(anthropic_messages[-1]["content"], list)
            ):
                anthropic_messages[-1]["content"].append(tool_result_block)
            else:
                anthropic_messages.append(
                    {"role": "user", "content": [tool_result_block]}
                )

        elif role == "user":
            content = _convert_content_blocks(message.get("content", ""))
            anthropic_msg = {"role": "user", "content": content}

            # Merge consecutive user messages (Anthropic doesn't allow them)
            if (
                anthropic_messages
                and anthropic_messages[-1]["role"] == "user"
                and isinstance(anthropic_messages[-1]["content"], list)
            ):
                if isinstance(content, list):
                    anthropic_messages[-1]["content"].extend(content)
                else:
                    anthropic_messages[-1]["content"].append(
                        {"type": "text", "text": str(content)}
                    )
            else:
                anthropic_messages.append(anthropic_msg)

        else:
            # Unknown role — skip with warning
            log.warning(f"Skipping message with unknown role: {role}")

    system_prompt = "\n\n".join(system_parts) if system_parts else None

    return system_prompt, anthropic_messages


def _convert_assistant_message(message: dict) -> dict:
    """Convert an OpenAI assistant message to Anthropic format."""
    content_blocks = []

    # Regular content
    msg_content = message.get("content")
    if msg_content:
        if isinstance(msg_content, str):
            content_blocks.append({"type": "text", "text": msg_content})
        elif isinstance(msg_content, list):
            content_blocks.extend(_convert_content_blocks(msg_content))

    # Tool calls → tool_use content blocks
    tool_calls = message.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            func = tc.get("function", {})
            arguments = func.get("arguments", "{}")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

            content_blocks.append(
                {
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": func.get("name", ""),
                    "input": arguments,
                }
            )

    # If no content at all, use empty text block (Anthropic requires non-empty content)
    if not content_blocks:
        content_blocks.append({"type": "text", "text": ""})

    return {"role": "assistant", "content": content_blocks}


def _convert_content_blocks(content) -> list[dict]:
    """
    Convert OpenAI content (string or list of parts) to Anthropic content blocks.
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    if not isinstance(content, list):
        return [{"type": "text", "text": str(content)}]

    blocks = []
    for part in content:
        if isinstance(part, str):
            blocks.append({"type": "text", "text": part})
        elif isinstance(part, dict):
            part_type = part.get("type", "")

            if part_type == "text":
                blocks.append({"type": "text", "text": part.get("text", "")})

            elif part_type == "image_url":
                image_block = _convert_image_url_to_anthropic(part)
                if image_block:
                    blocks.append(image_block)

            else:
                # Pass through unknown types as text
                log.debug(
                    f"Unknown content part type '{part_type}', converting to text"
                )
                text = part.get("text", part.get("content", str(part)))
                blocks.append({"type": "text", "text": str(text)})

    return blocks if blocks else [{"type": "text", "text": ""}]


def _convert_image_url_to_anthropic(part: dict) -> Optional[dict]:
    """
    Convert an OpenAI image_url content part to an Anthropic image content block.

    Handles both base64 data URIs and regular URLs.
    """
    image_url = part.get("image_url", {})
    url = image_url.get("url", "") if isinstance(image_url, dict) else str(image_url)

    if not url:
        return None

    if url.startswith("data:"):
        # Parse data URI: data:image/png;base64,iVBOR...
        match = re.match(r"data:(image/[^;]+);base64,(.+)", url, re.DOTALL)
        if match:
            media_type = match.group(1)
            data = match.group(2)
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            }
        else:
            log.warning("Could not parse data URI for image content")
            return None
    else:
        # Regular URL
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": url,
            },
        }


def convert_tools_openai_to_anthropic(tools: list[dict]) -> list[dict]:
    """
    Convert OpenAI tool definitions to Anthropic format.

    OpenAI: {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    Anthropic: {"name": "...", "description": "...", "input_schema": {...}}
    """
    anthropic_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            anthropic_tool = {
                "name": func.get("name", ""),
            }
            if "description" in func:
                anthropic_tool["description"] = func["description"]

            # parameters → input_schema
            params = func.get("parameters")
            if params:
                anthropic_tool["input_schema"] = params
            else:
                # Anthropic requires input_schema even if empty
                anthropic_tool["input_schema"] = {"type": "object", "properties": {}}

            anthropic_tools.append(anthropic_tool)
        else:
            # Non-function tool types — pass through with warning
            log.warning(f"Skipping non-function tool type: {tool.get('type')}")

    return anthropic_tools


def convert_tool_choice_openai_to_anthropic(tool_choice) -> dict:
    """
    Convert OpenAI tool_choice to Anthropic format.

    OpenAI: "auto" | "none" | "required" | {"type": "function", "function": {"name": "..."}}
    Anthropic: {"type": "auto"} | {"type": "any"} | {"type": "tool", "name": "..."}
    """
    if isinstance(tool_choice, str):
        if tool_choice == "none":
            # Anthropic doesn't have a "none" tool_choice — omit tools instead
            return {"type": "auto"}
        elif tool_choice == "required":
            return {"type": "any"}
        else:
            # "auto" or anything else
            return {"type": "auto"}

    elif isinstance(tool_choice, dict):
        func = tool_choice.get("function", {})
        name = func.get("name", "")
        if name:
            return {"type": "tool", "name": name}
        return {"type": "auto"}

    return {"type": "auto"}


def apply_model_params_to_body_anthropic(params: dict, form_data: dict) -> dict:
    """
    Apply model-level parameter overrides for Anthropic.
    Called before payload conversion when model_info has custom params.
    """
    params = remove_open_webui_params(params)

    custom_params = params.pop("custom_params", {})
    if custom_params:
        for key, value in custom_params.items():
            if isinstance(value, str):
                try:
                    custom_params[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        params = deep_update(params, custom_params)

    mappings = {
        "temperature": float,
        "top_p": float,
        "max_tokens": int,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
    }
    return apply_model_params_to_body(params, form_data, mappings)
