import json
import re
from datetime import timedelta
from uuid import uuid4
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)


def convert_ollama_tool_call_to_openai(tool_calls: list) -> list:
    openai_tool_calls = []
    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        openai_tool_call = {
            "index": tool_call.get("index", function.get("index", 0)),
            "id": tool_call.get("id", f"call_{str(uuid4())}"),
            "type": "function",
            "function": {
                "name": function.get("name", ""),
                "arguments": json.dumps(function.get("arguments", {})),
            },
        }
        openai_tool_calls.append(openai_tool_call)
    return openai_tool_calls


def convert_ollama_usage_to_openai(data: dict) -> dict:
    return {
        "response_token/s": (
            round(
                (
                    (
                        data.get("eval_count", 0)
                        / ((data.get("eval_duration", 0) / 10_000_000))
                    )
                    * 100
                ),
                2,
            )
            if data.get("eval_duration", 0) > 0
            else "N/A"
        ),
        "prompt_token/s": (
            round(
                (
                    (
                        data.get("prompt_eval_count", 0)
                        / ((data.get("prompt_eval_duration", 0) / 10_000_000))
                    )
                    * 100
                ),
                2,
            )
            if data.get("prompt_eval_duration", 0) > 0
            else "N/A"
        ),
        "total_duration": data.get("total_duration", 0),
        "load_duration": data.get("load_duration", 0),
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "prompt_tokens": int(
            data.get("prompt_eval_count", 0)
        ),  # This is the OpenAI compatible key
        "prompt_eval_duration": data.get("prompt_eval_duration", 0),
        "eval_count": data.get("eval_count", 0),
        "completion_tokens": int(
            data.get("eval_count", 0)
        ),  # This is the OpenAI compatible key
        "eval_duration": data.get("eval_duration", 0),
        "approximate_total": (lambda s: f"{s // 3600}h{(s % 3600) // 60}m{s % 60}s")(
            (data.get("total_duration", 0) or 0) // 1_000_000_000
        ),
        "total_tokens": int(  # This is the OpenAI compatible key
            data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        ),
        "completion_tokens_details": {  # This is the OpenAI compatible key
            "reasoning_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0,
        },
    }

def ms_to_seconds(ms): return round(ms / 1000, 3)

def seconds_to_hms(seconds):
    try:
        seconds_int = int(seconds)
        return str(timedelta(seconds=seconds_int))
    except (ValueError, TypeError):
        return "0h0m0s"



def safe_search(pattern, text, group_index=1, fallback="N/A", convert_func=lambda x: x):
    match = re.search(pattern, text)
    if match:
        try:
            return convert_func(match.group(group_index))
        except (IndexError, ValueError):
            return fallback
    return fallback

def extract_llama_cpp_metrics(perf_text):
    # Replace fixed spacing with flexible whitespace handling
    total_tokens = safe_search(r'total time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)', perf_text, convert_func=int, fallback=0)
    prompt_tokens = safe_search(r'prompt eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)', perf_text, convert_func=int, fallback=0)
    response_token_per_sec = safe_search(r'sampling time\s*=\s*[\d.]+\s*ms\s*/\s*[\d]+\s*runs\s*\(\s*[\d.]+ ms per token,\s*([\d.]+) tokens per second\)', perf_text, fallback="N/A")
    prompt_token_per_sec = safe_search(r'prompt eval time\s*=\s*[\d.]+\s*ms\s*/\s*[\d]+\s*tokens\s*\(\s*[\d.]+\s*ms per token,\s*([\d.]+)\s*tokens per second\)', perf_text, fallback="N/A")
    total_duration = safe_search(r'total time\s*=\s*([\d.]+)\s*ms', perf_text, convert_func=lambda x: ms_to_seconds(float(x)))
    load_duration = safe_search(r'load time\s*=\s*([\d.]+)\s*ms', perf_text, convert_func=lambda x: ms_to_seconds(float(x)))
    prompt_eval_count = safe_search(r'prompt eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)', perf_text, convert_func=int)
    prompt_eval_duration = safe_search(r'prompt eval time\s*=\s*([\d.]+)\s*ms', perf_text, convert_func=lambda x: ms_to_seconds(float(x)))
    eval_count = safe_search(r'eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)', perf_text, convert_func=int)
    eval_duration = safe_search(r'eval time\s*=\s*([\d.]+)\s*ms', perf_text, convert_func=lambda x: ms_to_seconds(float(x)))
    approximate_total = seconds_to_hms(safe_search(r'total time\s*=\s*([\d.]+)\s*ms', perf_text, convert_func=lambda x: ms_to_seconds(float(x))))

    metrics = {
            "response_token/s": response_token_per_sec,
            "prompt_token/s": prompt_token_per_sec,
            "total_duration": total_duration,
            "load_duration": load_duration,
            "prompt_eval_count": prompt_eval_count,
            "prompt_tokens": prompt_tokens,
            "prompt_eval_duration": prompt_eval_duration,
            "eval_count": eval_count,
            "completion_tokens": total_tokens - prompt_tokens,
            "eval_duration": eval_duration,
            "approximate_total": approximate_total,
            "total_tokens":total_tokens,
            "completion_tokens_details": {
                "reasoning_tokens": 0,
                "accepted_prediction_tokens": 0,
                "rejected_prediction_tokens": 0
            }
    }
    return metrics

# Print result

def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    model = ollama_response.get("model", "ollama")
    message_content = ollama_response.get("message", {}).get("content", "")
    reasoning_content = ollama_response.get("message", {}).get("thinking", None)
    tool_calls = ollama_response.get("message", {}).get("tool_calls", None)
    openai_tool_calls = None
    meta = ollama_response.get("message", {}).get("meta", "")

    if tool_calls:
        openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)

    data = ollama_response

    if meta:
        usage = extract_llama_cpp_metrics(meta)
    else:
        usage = convert_ollama_usage_to_openai(data)

    response = openai_chat_completion_message_template(
        model, message_content, reasoning_content, openai_tool_calls, usage
    )
    return response


async def convert_streaming_response_ollama_to_openai(ollama_streaming_response):
    async for data in ollama_streaming_response.body_iterator:
        data = json.loads(data)

        model = data.get("model", "ollama")
        message_content = data.get("message", {}).get("content", None)
        reasoning_content = data.get("message", {}).get("thinking", None)
        tool_calls = data.get("message", {}).get("tool_calls", None)
        openai_tool_calls = None
        message = data.get("message")
        if isinstance(message, dict):
            meta = message.get("meta", "No ollama meta")
        else:
            meta = "Message field not found or invalid"

        if tool_calls:
            openai_tool_calls = convert_ollama_tool_call_to_openai(tool_calls)

        done = data.get("done", False)

        if meta:
            usage = extract_llama_cpp_metrics(meta)
        else:
            usage = None

        if done and usage is None :
            usage = convert_ollama_usage_to_openai(data)

        data = openai_chat_chunk_message_template(
            model, message_content, reasoning_content, openai_tool_calls, usage
        )

        line = f"data: {json.dumps(data)}\n\n"
        yield line

    yield "data: [DONE]\n\n"


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
    # Ollama batch-style output
    if isinstance(response, dict) and "embeddings" in response:
        openai_data = []
        for i, emb in enumerate(response["embeddings"]):
            openai_data.append(
                {
                    "object": "embedding",
                    "embedding": emb.get("embedding"),
                    "index": emb.get("index", i),
                }
            )
        return {
            "object": "list",
            "data": openai_data,
            "model": response.get("model"),
        }
    # Ollama single output
    elif isinstance(response, dict) and "embedding" in response:
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": response["embedding"],
                    "index": 0,
                }
            ],
            "model": response.get("model"),
        }
    # Already OpenAI-compatible?
    elif (
        isinstance(response, dict)
        and "data" in response
        and isinstance(response["data"], list)
    ):
        return response

    # Fallback: return as is if unrecognized
    return response
