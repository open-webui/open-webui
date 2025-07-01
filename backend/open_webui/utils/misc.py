import hashlib
import re
import time
import uuid
import logging
from datetime import timedelta
from pathlib import Path
from typing import Callable, Optional
import json


import collections.abc
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def get_message_list(messages, message_id):
    """
    Reconstructs a list of messages in order up to the specified message_id.

    :param message_id: ID of the message to reconstruct the chain
    :param messages: Message history dict containing all messages
    :return: List of ordered messages starting from the root to the given message
    """

    # Handle case where messages is None
    if not messages:
        return []  # Return empty list instead of None to prevent iteration errors

    # Find the message by its id
    current_message = messages.get(message_id)

    if not current_message:
        return []  # Return empty list instead of None to prevent iteration errors

    # Reconstruct the chain by following the parentId links
    message_list = []

    while current_message:
        message_list.insert(
            0, current_message
        )  # Insert the message at the beginning of the list
        parent_id = current_message.get("parentId")  # Use .get() for safety
        current_message = messages.get(parent_id) if parent_id else None

    return message_list


def get_messages_content(messages: list[dict]) -> str:
    return "\n".join(
        [
            f"{message['role'].upper()}: {get_content_from_message(message)}"
            for message in messages
        ]
    )


def get_last_user_message_item(messages: list[dict]) -> Optional[dict]:
    for message in reversed(messages):
        if message["role"] == "user":
            return message
    return None


def get_content_from_message(message: dict) -> Optional[str]:
    if isinstance(message.get("content"), list):
        for item in message["content"]:
            if item["type"] == "text":
                return item["text"]
    else:
        return message.get("content")
    return None


def get_last_user_message(messages: list[dict]) -> Optional[str]:
    message = get_last_user_message_item(messages)
    if message is None:
        return None
    return get_content_from_message(message)


def get_last_assistant_message_item(messages: list[dict]) -> Optional[dict]:
    for message in reversed(messages):
        if message["role"] == "assistant":
            return message
    return None


def get_last_assistant_message(messages: list[dict]) -> Optional[str]:
    for message in reversed(messages):
        if message["role"] == "assistant":
            return get_content_from_message(message)
    return None


def get_system_message(messages: list[dict]) -> Optional[dict]:
    for message in messages:
        if message["role"] == "system":
            return message
    return None


def remove_system_message(messages: list[dict]) -> list[dict]:
    return [message for message in messages if message["role"] != "system"]


def pop_system_message(messages: list[dict]) -> tuple[Optional[dict], list[dict]]:
    return get_system_message(messages), remove_system_message(messages)


def prepend_to_first_user_message_content(
    content: str, messages: list[dict]
) -> list[dict]:
    for message in messages:
        if message["role"] == "user":
            if isinstance(message["content"], list):
                for item in message["content"]:
                    if item["type"] == "text":
                        item["text"] = f"{content}\n{item['text']}"
            else:
                message["content"] = f"{content}\n{message['content']}"
            break
    return messages


def add_or_update_system_message(
    content: str, messages: list[dict], append: bool = False
):
    """
    Adds a new system message at the beginning of the messages list
    or updates the existing system message at the beginning.

    :param msg: The message to be added or appended.
    :param messages: The list of message dictionaries.
    :return: The updated list of message dictionaries.
    """

    if messages and messages[0].get("role") == "system":
        if append:
            messages[0]["content"] = f"{messages[0]['content']}\n{content}"
        else:
            messages[0]["content"] = f"{content}\n{messages[0]['content']}"
    else:
        # Insert at the beginning
        messages.insert(0, {"role": "system", "content": content})

    return messages


def add_or_update_user_message(content: str, messages: list[dict]):
    """
    Adds a new user message at the end of the messages list
    or updates the existing user message at the end.

    :param msg: The message to be added or appended.
    :param messages: The list of message dictionaries.
    :return: The updated list of message dictionaries.
    """

    if messages and messages[-1].get("role") == "user":
        messages[-1]["content"] = f"{messages[-1]['content']}\n{content}"
    else:
        # Insert at the end
        messages.append({"role": "user", "content": content})

    return messages


def append_or_update_assistant_message(content: str, messages: list[dict]):
    """
    Adds a new assistant message at the end of the messages list
    or updates the existing assistant message at the end.

    :param msg: The message to be added or appended.
    :param messages: The list of message dictionaries.
    :return: The updated list of message dictionaries.
    """

    if messages and messages[-1].get("role") == "assistant":
        messages[-1]["content"] = f"{messages[-1]['content']}\n{content}"
    else:
        # Insert at the end
        messages.append({"role": "assistant", "content": content})

    return messages


def openai_chat_message_template(model: str):
    return {
        "id": f"{model}-{str(uuid.uuid4())}",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "logprobs": None, "finish_reason": None}],
    }


def openai_chat_chunk_message_template(
    model: str,
    content: Optional[str] = None,
    reasoning_content: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,
    usage: Optional[dict] = None,
) -> dict:
    template = openai_chat_message_template(model)
    template["object"] = "chat.completion.chunk"

    template["choices"][0]["index"] = 0
    template["choices"][0]["delta"] = {}

    if content:
        template["choices"][0]["delta"]["content"] = content

    if reasoning_content:
        template["choices"][0]["delta"]["reasoning_content"] = reasoning_content

    if tool_calls:
        template["choices"][0]["delta"]["tool_calls"] = tool_calls

    if not content and not tool_calls:
        template["choices"][0]["finish_reason"] = "stop"

    if usage:
        template["usage"] = usage
    return template


def openai_chat_completion_message_template(
    model: str,
    message: Optional[str] = None,
    reasoning_content: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,
    usage: Optional[dict] = None,
) -> dict:
    template = openai_chat_message_template(model)
    template["object"] = "chat.completion"
    if message is not None:
        template["choices"][0]["message"] = {
            "role": "assistant",
            "content": message,
            **({"reasoning_content": reasoning_content} if reasoning_content else {}),
            **({"tool_calls": tool_calls} if tool_calls else {}),
        }

    template["choices"][0]["finish_reason"] = "stop"

    if usage:
        template["usage"] = usage
    return template


def get_gravatar_url(email):
    # Trim leading and trailing whitespace from
    # an email address and force all characters
    # to lower case
    address = str(email).strip().lower()

    # Create a SHA256 hash of the final string
    hash_object = hashlib.sha256(address.encode())
    hash_hex = hash_object.hexdigest()

    # Grab the actual image URL
    return f"https://www.gravatar.com/avatar/{hash_hex}?d=mp"


def calculate_sha256(file_path, chunk_size):
    # Compute SHA-256 hash of a file efficiently in chunks
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_sha256_string(string):
    # Create a new SHA-256 hash object
    sha256_hash = hashlib.sha256()
    # Update the hash object with the bytes of the input string
    sha256_hash.update(string.encode("utf-8"))
    # Get the hexadecimal representation of the hash
    hashed_string = sha256_hash.hexdigest()
    return hashed_string


def validate_email_format(email: str) -> bool:
    if email.endswith("@localhost"):
        return True

    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def sanitize_filename(file_name):
    # Convert to lowercase
    lower_case_file_name = file_name.lower()

    # Remove special characters using regular expression
    sanitized_file_name = re.sub(r"[^\w\s]", "", lower_case_file_name)

    # Replace spaces with dashes
    final_file_name = re.sub(r"\s+", "-", sanitized_file_name)

    return final_file_name


def extract_folders_after_data_docs(path):
    # Convert the path to a Path object if it's not already
    path = Path(path)

    # Extract parts of the path
    parts = path.parts

    # Find the index of '/data/docs' in the path
    try:
        index_data_docs = parts.index("data") + 1
        index_docs = parts.index("docs", index_data_docs) + 1
    except ValueError:
        return []

    # Exclude the filename and accumulate folder names
    tags = []

    folders = parts[index_docs:-1]
    for idx, _ in enumerate(folders):
        tags.append("/".join(folders[: idx + 1]))

    return tags


def parse_duration(duration: str) -> Optional[timedelta]:
    if duration == "-1" or duration == "0":
        return None

    # Regular expression to find number and unit pairs
    pattern = r"(-?\d+(\.\d+)?)(ms|s|m|h|d|w)"
    matches = re.findall(pattern, duration)

    if not matches:
        raise ValueError("Invalid duration string")

    total_duration = timedelta()

    for number, _, unit in matches:
        number = float(number)
        if unit == "ms":
            total_duration += timedelta(milliseconds=number)
        elif unit == "s":
            total_duration += timedelta(seconds=number)
        elif unit == "m":
            total_duration += timedelta(minutes=number)
        elif unit == "h":
            total_duration += timedelta(hours=number)
        elif unit == "d":
            total_duration += timedelta(days=number)
        elif unit == "w":
            total_duration += timedelta(weeks=number)

    return total_duration


def parse_ollama_modelfile(model_text):
    parameters_meta = {
        "mirostat": int,
        "mirostat_eta": float,
        "mirostat_tau": float,
        "num_ctx": int,
        "repeat_last_n": int,
        "repeat_penalty": float,
        "temperature": float,
        "seed": int,
        "tfs_z": float,
        "num_predict": int,
        "top_k": int,
        "top_p": float,
        "num_keep": int,
        "typical_p": float,
        "presence_penalty": float,
        "frequency_penalty": float,
        "penalize_newline": bool,
        "numa": bool,
        "num_batch": int,
        "num_gpu": int,
        "main_gpu": int,
        "low_vram": bool,
        "f16_kv": bool,
        "vocab_only": bool,
        "use_mmap": bool,
        "use_mlock": bool,
        "num_thread": int,
    }

    data = {"base_model_id": None, "params": {}}

    # Parse base model
    base_model_match = re.search(
        r"^FROM\s+(\w+)", model_text, re.MULTILINE | re.IGNORECASE
    )
    if base_model_match:
        data["base_model_id"] = base_model_match.group(1)

    # Parse template
    template_match = re.search(
        r'TEMPLATE\s+"""(.+?)"""', model_text, re.DOTALL | re.IGNORECASE
    )
    if template_match:
        data["params"] = {"template": template_match.group(1).strip()}

    # Parse stops
    stops = re.findall(r'PARAMETER stop "(.*?)"', model_text, re.IGNORECASE)
    if stops:
        data["params"]["stop"] = stops

    # Parse other parameters from the provided list
    for param, param_type in parameters_meta.items():
        param_match = re.search(rf"PARAMETER {param} (.+)", model_text, re.IGNORECASE)
        if param_match:
            value = param_match.group(1)

            try:
                if param_type is int:
                    value = int(value)
                elif param_type is float:
                    value = float(value)
                elif param_type is bool:
                    value = value.lower() == "true"
            except Exception as e:
                log.exception(f"Failed to parse parameter {param}: {e}")
                continue

            data["params"][param] = value

    # Parse adapter
    adapter_match = re.search(r"ADAPTER (.+)", model_text, re.IGNORECASE)
    if adapter_match:
        data["params"]["adapter"] = adapter_match.group(1)

    # Parse system description
    system_desc_match = re.search(
        r'SYSTEM\s+"""(.+?)"""', model_text, re.DOTALL | re.IGNORECASE
    )
    system_desc_match_single = re.search(
        r"SYSTEM\s+([^\n]+)", model_text, re.IGNORECASE
    )

    if system_desc_match:
        data["params"]["system"] = system_desc_match.group(1).strip()
    elif system_desc_match_single:
        data["params"]["system"] = system_desc_match_single.group(1).strip()

    # Parse messages
    messages = []
    message_matches = re.findall(r"MESSAGE (\w+) (.+)", model_text, re.IGNORECASE)
    for role, content in message_matches:
        messages.append({"role": role, "content": content})

    if messages:
        data["params"]["messages"] = messages

    return data


def convert_logit_bias_input_to_json(user_input):
    logit_bias_pairs = user_input.split(",")
    logit_bias_json = {}
    for pair in logit_bias_pairs:
        token, bias = pair.split(":")
        token = str(token.strip())
        bias = int(bias.strip())
        bias = 100 if bias > 100 else -100 if bias < -100 else bias
        logit_bias_json[token] = bias
    return json.dumps(logit_bias_json)
