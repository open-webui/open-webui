from open_webui.utils.task import prompt_template
from open_webui.utils.misc import (
    openai_chat_completion_message_template,
)

from typing import Callable, Optional


def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    model = ollama_response.get("model", "ollama")
    message_content = ollama_response.get("message", {}).get("content", "")

    response = openai_chat_completion_message_template(model, message_content)
    return response
