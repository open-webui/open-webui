"""
Streaming-related utilities for OpenAI API
"""


def convert_from_stream_headers(headers: dict) -> dict:
    """
    Convert headers from a stream to a dictionary
    Args:
        headers: Headers from a stream

    Returns: Dictionary of headers

    """
    # remove content-type and content-encoding headers in any case
    nostream_headers = {
        k: v
        for k, v in headers.items()
        if k.lower() not in ["content-type", "content-encoding"]
    }
    nostream_headers["Content-Type"] = "text/event-stream; charset=utf-8"
    return nostream_headers


import json
from typing import Any


def encode_sse_chunk(chunk: str | list | dict) -> bytes:
    """
    Encode data as an SSE (Server-Sent Events) message.

    Args:
        chunk (str | list | dict): The data to encode.

    Returns:
        A bytes object representing an SSE message.
    """
    if isinstance(chunk, (list, dict)):
        data = json.dumps(chunk, separators=(",", ":"))
    else:
        data = chunk
    return f"data: {data}\n\n".encode("utf-8")


def convert_to_stream_data(response_data: dict) -> list[bytes]:
    """
    Convert a response data dictionary to a list of SSE-formatted byte strings.

    Args:
        response_data: A dictionary containing the API response data.

    Returns:
        A list of SSE-formatted byte strings.
    """
    # Extract necessary information
    id = response_data["id"]
    created = response_data["created"]
    model = response_data["model"]
    system_fingerprint = response_data.get("system_fingerprint", "")
    content = response_data["choices"][0]["message"]["content"]

    # Create the base structure for each chunk
    base_chunk = {
        "id": id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "system_fingerprint": system_fingerprint,
        "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": None}],
    }

    # Create the stream
    stream = []

    # Add the initial chunk with role
    initial_chunk = base_chunk.copy()
    initial_chunk["choices"][0]["delta"] = {
        "role": "assistant",
        "content": "",
        "refusal": None,
    }
    stream.append(encode_sse_chunk(initial_chunk))

    # Add chunk for the entire content
    content_chunk = base_chunk.copy()
    content_chunk["choices"][0]["delta"] = {"content": content}
    stream.append(encode_sse_chunk(content_chunk))

    # Add the final chunk
    final_chunk = base_chunk.copy()
    final_chunk["choices"][0]["delta"] = {}
    final_chunk["choices"][0]["finish_reason"] = "stop"
    stream.append(encode_sse_chunk(final_chunk))

    # Add the [DONE] marker
    stream.append(encode_sse_chunk("[DONE]"))

    return stream
