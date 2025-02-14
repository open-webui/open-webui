import json
from uuid import uuid4
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)

def convert_response_ollama_usage_to_openai(data: dict) -> dict:
    return {
        "prompt_tokens": int(data.get("prompt_eval_count", 0)),
        "completion_tokens": int(data.get("eval_count", 0)),
        "total_tokens": int(
            data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        ),
        "completion_tokens_details": {
            "reasoning_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0
        }
    }

def convert_ollama_tool_call_to_openai(tool_calls: dict) -> dict:
    openai_tool_calls = []
    for tool_call in tool_calls:
        openai_tool_call = {
            "index": tool_call.get("index", 0),
            "id": tool_call.get("id", f"call_{str(uuid4())}"),
            "type": "function",
            "function": {
                "name": tool_call.get("function", {}).get("name", ""),
                "arguments": json.dumps(
                    tool_call.get("function", {}).get("arguments", {})
                ),
            },
        }
        openai_tool_calls.append(openai_tool_call)
    return openai_tool_calls


def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    model = ollama_response.get("model", "ollama")
    message_content = ollama_response.get("message", {}).get("content", "")
    tool_calls = ollama_response.get("message", {}).get("tool_calls", None)
    openai_tool_calls = None

    if tool_calls:
        openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)

    data = ollama_response

    usage = convert_response_ollama_usage_to_openai(data)

    response = openai_chat_completion_message_template(
        model, message_content, openai_tool_calls, usage
    )
    return response


async def convert_streaming_response_ollama_to_openai(ollama_streaming_response):
    async for data in ollama_streaming_response.body_iterator:
        data = json.loads(data)

        model = data.get("model", "ollama")
        message_content = data.get("message", {}).get("content", "")
        tool_calls = data.get("message", {}).get("tool_calls", None)
        openai_tool_calls = None

        if tool_calls:
            openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)

        done = data.get("done", False)

        usage = None
        if done:
            usage = convert_response_ollama_usage_to_openai(data)

        data = openai_chat_chunk_message_template(
            model, message_content if not done else None, openai_tool_calls, usage
        )

        line = f"data: {json.dumps(data)}\n\n"
        yield line

    yield "data: [DONE]\n\n"
