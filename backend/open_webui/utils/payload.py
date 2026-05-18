from open_webui.utils.task import prompt_template, prompt_variables_template
from open_webui.utils.misc import (
    deep_update,
    add_or_update_system_message,
    replace_system_message_content,
)

from typing import Callable, Optional
import json
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - py<3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]


def _resolve_local_now(metadata: Optional[dict]) -> tuple[datetime, str]:
    """Return (now, label) where ``now`` is the current time in the user's local timezone
    (when supplied via ``metadata['timezone']``) and ``label`` is the timezone identifier
    to surface in the system prompt. Falls back to server time / ``UTC`` label when the
    timezone is missing or invalid — matching the historical behaviour."""
    tz_name = (metadata or {}).get("timezone") if isinstance(metadata, dict) else None
    if tz_name and ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name)), tz_name
        except Exception:
            pass
    return datetime.now(), "UTC"


def apply_system_prompt_to_body(
    system: Optional[str],
    form_data: dict,
    metadata: Optional[dict] = None,
    user=None,
    replace: bool = False,
) -> dict:
    """Returns a new ``form_data`` with the system prompt applied. Pure: does not mutate
    ``form_data`` or its message list."""
    now, tz_label = _resolve_local_now(metadata)
    date_str = now.strftime("%Y-%m-%d")
    date_prompt = f"Current Date: {date_str} ({tz_label})"

    if not system:
        system = date_prompt
    else:
        if date_prompt not in system:
            system = f"{system}\n{date_prompt}"

    if metadata:
        variables = metadata.get("variables", {})
        if variables:
            system = prompt_variables_template(system, variables)

    system = prompt_template(system, user)

    messages = list(form_data.get("messages") or [])
    if replace:
        new_messages = replace_system_message_content(system, messages)
    else:
        new_messages = add_or_update_system_message(system, messages)

    return {**form_data, "messages": new_messages}


def apply_model_params_to_body(
    params: dict, form_data: dict, mappings: dict[str, Callable]
) -> dict:
    """Returns a new ``form_data`` with the params applied. Pure."""
    if not params:
        return form_data

    out = {**form_data}
    for key, value in params.items():
        if value is not None:
            if key in mappings:
                cast_func = mappings[key]
                if isinstance(cast_func, Callable):
                    out[key] = cast_func(value)
            else:
                out[key] = value

    return out


def _with_cache_control(message: dict) -> dict:
    """Return a copy of ``message`` whose final content part carries an ephemeral
    cache_control marker. String content is reshaped into a single text-part list to
    accommodate the marker. Pure: does not mutate ``message``."""
    content = message.get("content")

    if isinstance(content, list) and content:
        new_parts = list(content)
        last_part = new_parts[-1]
        if isinstance(last_part, dict):
            new_parts[-1] = {**last_part, "cache_control": {"type": "ephemeral"}}
        return {**message, "content": new_parts}

    if isinstance(content, str):
        return {
            **message,
            "content": [
                {
                    "type": "text",
                    "text": content,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }

    return message


def apply_ephemeral_cache_control_to_last_message(
    form_data: dict, enabled: bool = True
) -> dict:
    """Return a new ``form_data`` whose last message carries an ephemeral cache_control
    marker on its final content part. Pure: previous-round messages stay byte-stable
    across the live tool-call loop because their original objects are never mutated."""
    if not enabled:
        return form_data

    messages = form_data.get("messages")
    if not isinstance(messages, list) or not messages:
        return form_data

    last_message = messages[-1]
    if not isinstance(last_message, dict):
        return form_data

    return {**form_data, "messages": [*messages[:-1], _with_cache_control(last_message)]}


def remove_open_webui_params(params: dict) -> dict:
    """Returns a new params dict with OpenWebUI-specific keys removed. Pure."""
    open_webui_params = {
        "stream_response",
        "stream_delta_chunk_size",
        "function_calling",
        "reasoning_tags",
        "system",
    }
    return {k: v for k, v in params.items() if k not in open_webui_params}


def apply_model_params_to_body_openai(params: dict, form_data: dict) -> dict:
    """Returns a new ``form_data`` with OpenAI-shape model params applied. Pure."""
    params = remove_open_webui_params(params)
    params = dict(params)  # local copy so .pop is safe

    # service_tier is a per-request user choice (selected from the UI), not a
    # model-level default. ModelParams allows extra="allow" so a stray value
    # can persist in model.params from old data; without this strip, the
    # open-ended else: out[key] = value in apply_model_params_to_body would
    # silently override the request's tier with the model's stale one.
    params.pop("service_tier", None)

    custom_params = params.pop("custom_params", {})
    if custom_params:
        custom_params = dict(custom_params)
        for key, value in list(custom_params.items()):
            if isinstance(value, str):
                try:
                    custom_params[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        params = deep_update(dict(params), custom_params)

    mappings = {
        "temperature": float,
        "top_p": float,
        "min_p": float,
        "max_tokens": int,
        "frequency_penalty": float,
        "presence_penalty": float,
        "reasoning_effort": str,
        "seed": lambda x: x,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
        "logit_bias": lambda x: x,
        "response_format": dict,
    }
    return apply_model_params_to_body(params, form_data, mappings)


def apply_model_params_to_body_ollama(params: dict, form_data: dict) -> dict:
    """Returns a new ``form_data`` with Ollama-shape model params applied. Pure."""
    params = remove_open_webui_params(params)
    params = dict(params)

    custom_params = params.pop("custom_params", {})
    if custom_params:
        custom_params = dict(custom_params)
        for key, value in list(custom_params.items()):
            if isinstance(value, str):
                try:
                    custom_params[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        params = deep_update(dict(params), custom_params)

    name_differences = {
        "max_tokens": "num_predict",
    }

    for key, value in name_differences.items():
        if (param := params.get(key, None)) is not None:
            params[value] = params[key]
            del params[key]

    mappings = {
        "temperature": float,
        "top_p": float,
        "seed": lambda x: x,
        "mirostat": int,
        "mirostat_eta": float,
        "mirostat_tau": float,
        "num_ctx": int,
        "num_batch": int,
        "num_keep": int,
        "num_predict": int,
        "repeat_last_n": int,
        "top_k": int,
        "min_p": float,
        "repeat_penalty": float,
        "presence_penalty": float,
        "frequency_penalty": float,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
        "num_gpu": int,
        "use_mmap": bool,
        "use_mlock": bool,
        "num_thread": int,
    }

    def parse_json(value: str) -> dict:
        try:
            return json.loads(value)
        except Exception:
            return value

    ollama_root_params = {
        "format": lambda x: parse_json(x),
        "keep_alive": lambda x: parse_json(x),
        "think": bool,
    }

    out = {**form_data}
    for key, value in ollama_root_params.items():
        if (param := params.get(key, None)) is not None:
            out[key] = value(param)
            del params[key]

    out["options"] = apply_model_params_to_body(
        params, dict(form_data.get("options") or {}), mappings
    )
    return out


def convert_messages_openai_to_ollama(messages: list[dict]) -> list[dict]:
    ollama_messages = []

    for message in messages:
        new_message = {"role": message["role"]}

        content = message.get("content", [])
        tool_calls = message.get("tool_calls", None)
        tool_call_id = message.get("tool_call_id", None)

        if isinstance(content, str) and not tool_calls:
            new_message["content"] = content

            if tool_call_id:
                new_message["tool_call_id"] = tool_call_id

        elif tool_calls:
            ollama_tool_calls = []
            for tool_call in tool_calls:
                ollama_tool_call = {
                    "index": tool_call.get("index", 0),
                    "id": tool_call.get("id", None),
                    "function": {
                        "name": tool_call.get("function", {}).get("name", ""),
                        "arguments": json.loads(
                            tool_call.get("function", {}).get("arguments", {})
                        ),
                    },
                }
                ollama_tool_calls.append(ollama_tool_call)
            new_message["tool_calls"] = ollama_tool_calls

            new_message["content"] = ""

        else:
            content_text = ""
            images = []

            for item in content:
                if item.get("type") == "text":
                    content_text += item.get("text", "")

                elif item.get("type") == "image_url":
                    img_url = item.get("image_url", {}).get("url", "")
                    if img_url:
                        if img_url.startswith("data:"):
                            img_url = img_url.split(",")[-1]
                        images.append(img_url)

            if content_text:
                new_message["content"] = content_text.strip()

            if images:
                new_message["images"] = images

        ollama_messages.append(new_message)

    return ollama_messages


def convert_payload_openai_to_ollama(openai_payload: dict) -> dict:
    """
    Converts a payload formatted for OpenAI's API to be compatible with Ollama's API endpoint for chat completions.

    Args:
        openai_payload (dict): The payload originally designed for OpenAI API usage.

    Returns:
        dict: A modified payload compatible with the Ollama API.
    """
    ollama_payload = {}

    ollama_payload["model"] = openai_payload.get("model")
    ollama_payload["messages"] = convert_messages_openai_to_ollama(
        openai_payload.get("messages")
    )
    ollama_payload["stream"] = openai_payload.get("stream", False)
    if "tools" in openai_payload:
        ollama_payload["tools"] = openai_payload["tools"]

    if openai_payload.get("options"):
        ollama_payload["options"] = openai_payload["options"]
        ollama_options = openai_payload["options"]

        def parse_json(value: str) -> dict:
            try:
                return json.loads(value)
            except Exception:
                return value

        ollama_root_params = {
            "format": lambda x: parse_json(x),
            "keep_alive": lambda x: parse_json(x),
            "think": bool,
        }

        for key, value in ollama_root_params.items():
            if (param := ollama_options.get(key, None)) is not None:
                ollama_payload[key] = value(param)
                del ollama_options[key]

        if "max_tokens" in ollama_options:
            ollama_options["num_predict"] = ollama_options["max_tokens"]
            del ollama_options["max_tokens"]

        if "system" in ollama_options:
            ollama_payload["system"] = ollama_options["system"]
            del ollama_options["system"]

        ollama_payload["options"] = ollama_options

    if "stop" in openai_payload:
        ollama_options = ollama_payload.get("options", {})
        ollama_options["stop"] = openai_payload.get("stop")
        ollama_payload["options"] = ollama_options

    if "metadata" in openai_payload:
        ollama_payload["metadata"] = openai_payload["metadata"]

    if "response_format" in openai_payload:
        response_format = openai_payload["response_format"]
        format_type = response_format.get("type", None)

        schema = response_format.get(format_type, None)
        if schema:
            format = schema.get("schema", None)
            ollama_payload["format"] = format

    return ollama_payload


def convert_embedding_payload_openai_to_ollama(openai_payload: dict) -> dict:
    """
    Convert an embeddings request payload from OpenAI format to Ollama format.

    Args:
        openai_payload (dict): The original payload designed for OpenAI API usage.

    Returns:
        dict: A payload compatible with the Ollama API embeddings endpoint.
    """
    ollama_payload = {"model": openai_payload.get("model")}
    input_value = openai_payload.get("input")

    if isinstance(input_value, list):
        ollama_payload["input"] = input_value
        ollama_payload["prompt"] = "\n".join(str(x) for x in input_value)
    else:
        ollama_payload["input"] = [input_value]
        ollama_payload["prompt"] = str(input_value)

    for optional_key in ("options", "truncate", "keep_alive"):
        if optional_key in openai_payload:
            ollama_payload[optional_key] = openai_payload[optional_key]

    return ollama_payload
