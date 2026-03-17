"""
Patched streaming response helpers for Open WebUI

Fix: Accumulate partial text chunks into a buffer and parse newline-delimited
JSON messages. This prevents JSON decode errors when SSE/text chunks are
split across `aiter_text()` yields.

This file is intended as a small, focused change to replicate the runtime
fix applied in the LEO project. It mirrors behaviour expected by Open WebUI's
streaming code: yield OpenAI-style 'data: {json}\n\n' chunks and emit a
final '[DONE]' marker when the stream finishes.
"""
from __future__ import annotations

import json
from typing import AsyncIterator


async def stream_text_lines_to_json(async_text_iter) -> AsyncIterator[dict]:
    """Convert an async iterator of text chunks into parsed JSON objects.

    The source may yield arbitrary slices of text (partial JSON lines). This
    helper accumulates bytes into an internal buffer and yields complete JSON
    objects when a newline is observed. It ignores empty lines.
    """
    _buffer = ""
    async for text in async_text_iter:
        if not text:
            continue
        _buffer += text
        while "\n" in _buffer:
            line, _buffer = _buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            # Some producers may prefix with 'data: ' (SSE style); strip it.
            if line.startswith("data:"):
                line = line[len("data:"):].strip()
            try:
                obj = json.loads(line)
            except Exception:
                # If parsing fails, keep the line in the buffer for the next
                # iteration (it might be a partial JSON object). Prepend and
                # break to await more data.
                _buffer = line + "\n" + _buffer
                break
            yield obj


async def json_objs_to_openai_stream(async_text_iter) -> AsyncIterator[str]:
    """Yield OpenAI-compatible streaming chunks (text/event like) as strings.

    Each parsed JSON object is wrapped as a "data: <json>\n\n" chunk.
    At the end of the iterator, a final "data: [DONE]\n\n" chunk is yielded.
    """
    try:
        async for obj in stream_text_lines_to_json(async_text_iter):
            yield f"data: {json.dumps(obj)}\n\n"
    finally:
        # Signal stream end to consumers that expect the OpenAI style sentinel.
        yield "data: [DONE]\n\n"
