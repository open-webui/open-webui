from open_webui.utils.task import prompt_template, prompt_variables_template
from open_webui.utils.misc import (
    add_or_update_system_message,
)

from typing import Callable, Optional, List
import json
import transformers


def count_input_tokens(messages: List[dict], model: str) -> int:
    """Count input tokens for a given model and messages."""
    try:
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            "./deepseek_v3_tokenizer", trust_remote_code=True
        )
        total_tokens = 0
        for msg in messages:
            if isinstance(msg.get("content"), str):
                total_tokens += len(tokenizer.encode(msg["content"]))
        return total_tokens
    except Exception as e:
        return 0


def calculate_adjusted_max_tokens(
    model: str,
    user_max: int,
    messages: Optional[List[dict]] = None,
    max_context: Optional[int] = None,
) -> int:
    """Calculate adjusted max tokens based on model context size.
    If max_context is set, it will override any user_max setting and calculate
    max tokens automatically based on input length.
    """

    if max_context is not None and messages is not None:
        input_tokens = count_input_tokens(messages, model)

        # Calculate available tokens without considering user_max, 1000 is a buffer
        result = max(128, max_context - input_tokens - 1000)
        return result

    return user_max


# inplace function: form_data is modified
def apply_model_system_prompt_to_body(
    params: dict, form_data: dict, metadata: Optional[dict] = None, user=None
) -> dict:
    system = params.get("system", None)
    if not system:
        return form_data

    # Metadata (WebUI Usage)
    if metadata:
        variables = metadata.get("variables", {})
        if variables:
            system = prompt_variables_template(system, variables)

    # Legacy (API Usage)
    if user:
        template_params = {
            "user_name": user.name,
            "user_location": user.info.get("location") if user.info else None,
        }
    else:
        template_params = {}

    system = prompt_template(system, **template_params)

    form_data["messages"] = add_or_update_system_message(
        system, form_data.get("messages", [])
    )
    return form_data


# inplace function: form_data is modified
def apply_model_params_to_body(
    params: dict, form_data: dict, mappings: dict[str, Callable]
) -> dict:
    if not params:
        return form_data

    # First pass: Apply all parameters except max_tokens
    for key, cast_func in mappings.items():
        if key != "max_tokens" and (value := params.get(key)) is not None:
            form_data[key] = cast_func(value)

    # Second pass: Handle max_tokens with max_context if enabled
    if params.get("enable_max_context") and params.get("max_context") is not None:
        max_context = params["max_context"]
        user_max = params.get("max_tokens", 128)  # Default to 128 if not set

        adjusted_max = calculate_adjusted_max_tokens(
            form_data.get("model", ""),
            user_max,
            form_data.get("messages"),
            max_context,
        )
        form_data["max_tokens"] = adjusted_max
    elif "max_tokens" in mappings and params.get("max_tokens") is not None:
        form_data["max_tokens"] = mappings["max_tokens"](params["max_tokens"])

    return form_data


# inplace function: form_data is modified
def apply_model_params_to_body_openai(params: dict, form_data: dict) -> dict:
    mappings = {
        "temperature": float,
        "top_p": float,
        "max_tokens": int,
        "frequency_penalty": float,
        "reasoning_effort": str,
        "seed": lambda x: x,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
        "enable_max_context": bool,
        "max_context": int,
    }
    return apply_model_params_to_body(params, form_data, mappings)


def apply_model_params_to_body_ollama(params: dict, form_data: dict) -> dict:
    # Convert OpenAI parameter names to Ollama parameter names if needed.
    name_differences = {
        "max_tokens": "num_predict",
    }

    for key, value in name_differences.items():
        if (param := params.get(key, None)) is not None:
            # Copy the parameter to new name then delete it, to prevent Ollama warning of invalid option provided
            params[value] = params[key]
            del params[key]

    # See https://github.com/ollama/ollama/blob/main/docs/api.md#request-8
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
        "typical_p": float,
        "repeat_penalty": float,
        "presence_penalty": float,
        "frequency_penalty": float,
        "penalize_newline": bool,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
        "numa": bool,
        "num_gpu": int,
        "main_gpu": int,
        "low_vram": bool,
        "vocab_only": bool,
        "use_mmap": bool,
        "use_mlock": bool,
        "num_thread": int,
    }

    return apply_model_params_to_body(params, form_data, mappings)


def convert_messages_openai_to_ollama(messages: list[dict]) -> list[dict]:
    ollama_messages = []

    for message in messages:
        # Initialize the new message structure with the role
        new_message = {"role": message["role"]}

        content = message.get("content", [])
        tool_calls = message.get("tool_calls", None)
        tool_call_id = message.get("tool_call_id", None)

        # Check if the content is a string (just a simple message)
        if isinstance(content, str):
            # If the content is a string, it's pure text
            new_message["content"] = content

            # If message is a tool call, add the tool call id to the message
            if tool_call_id:
                new_message["tool_call_id"] = tool_call_id

        elif tool_calls:
            # If tool calls are present, add them to the message
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

            # Put the content to empty string (Ollama requires an empty string for tool calls)
            new_message["content"] = ""

        else:
            # Otherwise, assume the content is a list of dicts, e.g., text followed by an image URL
            content_text = ""
            images = []

            # Iterate through the list of content items
            for item in content:
                # Check if it's a text type
                if item.get("type") == "text":
                    content_text += item.get("text", "")

                # Check if it's an image URL type
                elif item.get("type") == "image_url":
                    img_url = item.get("image_url", {}).get("url", "")
                    if img_url:
                        # If the image url starts with data:, it's a base64 image and should be trimmed
                        if img_url.startswith("data:"):
                            img_url = img_url.split(",")[-1]
                        images.append(img_url)

            # Add content text (if any)
            if content_text:
                new_message["content"] = content_text.strip()

            # Add images (if any)
            if images:
                new_message["images"] = images

        # Append the new formatted message to the result
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

    # Mapping basic model and message details
    ollama_payload["model"] = openai_payload.get("model")
    ollama_payload["messages"] = convert_messages_openai_to_ollama(
        openai_payload.get("messages")
    )
    ollama_payload["stream"] = openai_payload.get("stream", False)

    if "tools" in openai_payload:
        ollama_payload["tools"] = openai_payload["tools"]

    if "format" in openai_payload:
        ollama_payload["format"] = openai_payload["format"]

    # If there are advanced parameters in the payload, format them in Ollama's options field
    if openai_payload.get("options"):
        ollama_payload["options"] = openai_payload["options"]
        ollama_options = openai_payload["options"]

        # Handle parameters which map directly
        for param in ["temperature", "top_p", "seed"]:
            if param in openai_payload:
                ollama_options[param] = openai_payload[param]

        # Re-Mapping OpenAI's `max_tokens` -> Ollama's `num_predict` with dynamic adjustment
        if "max_tokens" in ollama_options or "max_context" in ollama_options:
            model = openai_payload.get("model", "")
            user_max = ollama_options.get(
                "max_tokens", 128
            )  # Default to 128 if not set
            max_context = ollama_options.get("max_context")

            adjusted_max = calculate_adjusted_max_tokens(
                model,
                user_max,
                ollama_payload.get("messages"),
                max_context,
            )

            ollama_options["num_predict"] = adjusted_max

            # Remove max_context and max_tokens from options to prevent Ollama warning
            if "max_context" in ollama_options:
                del ollama_options["max_context"]
            if "max_tokens" in ollama_options:
                del ollama_options["max_tokens"]

        # Mapping OpenAI's `max_tokens` -> Ollama's `num_predict`
        if "max_completion_tokens" in openai_payload:
            ollama_options["num_predict"] = openai_payload["max_completion_tokens"]
        elif "max_tokens" in openai_payload:
            ollama_options["num_predict"] = openai_payload["max_tokens"]

        # Handle frequency / presence_penalty, which needs renaming and checking
        if "frequency_penalty" in openai_payload:
            ollama_options["repeat_penalty"] = openai_payload["frequency_penalty"]

        if "presence_penalty" in openai_payload and "penalty" not in ollama_options:
            # We are assuming presence penalty uses a similar concept in Ollama, which needs custom handling if exists.
            ollama_options["new_topic_penalty"] = openai_payload["presence_penalty"]

        # Handle system prompt
        if "system" in ollama_options:
            ollama_payload["system"] = ollama_options["system"]
            del ollama_options[
                "system"
            ]  # To prevent Ollama warning of invalid option provided

        # Add options to payload if any have been set
        if ollama_options:
            ollama_payload["options"] = ollama_options

    if "metadata" in openai_payload:
        ollama_payload["metadata"] = openai_payload["metadata"]

    return ollama_payload
