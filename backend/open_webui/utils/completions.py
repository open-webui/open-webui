import json
import logging
import time as _time
import uuid as _uuid

log = logging.getLogger(__name__)


# Keys that only exist in the legacy (text) completions request and must NOT
# be forwarded to the Chat Completions handler.
LEGACY_ONLY_KEYS = {"prompt", "suffix", "echo", "best_of", "logprobs"}


def normalize_completion_prompt(prompt) -> str:
    """
    Normalize the OpenAI legacy ``prompt`` field to a single string.

    The OpenAI spec allows ``prompt`` to be a string, an array of strings, or an
    array of token arrays. We support string and array-of-strings (joined with
    newlines); anything else is coerced to ``str`` as a best effort.
    """
    if prompt is None:
        return ""
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        parts = []
        for p in prompt:
            parts.append(p if isinstance(p, str) else str(p))
        return "\n".join(parts)
    return str(prompt)


def convert_completions_to_chat_payload(form_data: dict) -> dict:
    """
    Convert an OpenAI legacy (text) completions payload to the Chat Completions
    payload understood by the internal chat completion pipeline.

    The ``prompt`` is forwarded verbatim as a single user message so callers
    (e.g. continue.dev autocomplete) can supply their own FIM template. When a
    ``suffix`` is provided we fall back to a best-effort fill-in-the-middle
    framing, since chat models cannot natively insert between prefix/suffix.
    All other recognized sampling parameters (``max_tokens``, ``temperature``,
    ``top_p``, ``n``, ``stream``, ``stop``, ``presence_penalty``,
    ``frequency_penalty``, ``seed``, ``user``, ...) are passed through as-is.
    """
    prompt_text = normalize_completion_prompt(form_data.get("prompt", ""))
    suffix = form_data.get("suffix") or ""

    if suffix:
        content = (
            "You are a fill-in-the-middle completion engine. Output only the "
            "text that belongs between <prefix> and <suffix>, with no "
            "explanation or surrounding markup.\n"
            f"<prefix>{prompt_text}</prefix>\n<suffix>{suffix}</suffix>"
        )
    else:
        content = prompt_text

    chat_payload = {k: v for k, v in form_data.items() if k not in LEGACY_ONLY_KEYS}
    chat_payload["messages"] = [{"role": "user", "content": content}]
    return chat_payload


def convert_chat_to_completions_response(
    chat_response: dict, model: str = "", echo_prompt: str = ""
) -> dict:
    """
    Convert a non-streaming Chat Completions response to the legacy
    ``text_completion`` response shape.
    """
    choices_out = []
    for choice in chat_response.get("choices", []) or []:
        message = choice.get("message", {}) or {}
        text = message.get("content") or ""
        if echo_prompt:
            text = echo_prompt + text
        choices_out.append(
            {
                "text": text,
                "index": choice.get("index", len(choices_out)),
                "logprobs": None,
                "finish_reason": choice.get("finish_reason", "stop"),
            }
        )

    if not choices_out:
        choices_out = [
            {
                "text": echo_prompt or "",
                "index": 0,
                "logprobs": None,
                "finish_reason": "stop",
            }
        ]

    response_id = chat_response.get("id") or f"cmpl-{_uuid.uuid4().hex}"
    response_id = response_id.replace("chatcmpl-", "cmpl-")

    return {
        "id": response_id,
        "object": "text_completion",
        "created": chat_response.get("created", int(_time.time())),
        "model": model or chat_response.get("model", ""),
        "choices": choices_out,
        "usage": chat_response.get("usage", {}),
    }


async def chat_stream_to_completions_stream(
    chat_stream_generator, model: str = "", echo_prompt: str = ""
):
    """
    Convert a Chat Completions SSE stream to a legacy completions SSE stream.

    Chat sends: ``data: {"choices": [{"delta": {"content": "..."}}]}``
    Legacy sends: ``data: {"object": "text_completion", "choices": [{"text": "..."}]}``
    """
    cmpl_id = f"cmpl-{_uuid.uuid4().hex}"
    created = int(_time.time())

    def _make_chunk(text, index, finish_reason, usage=None):
        chunk = {
            "id": cmpl_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "text": text,
                    "index": index,
                    "logprobs": None,
                    "finish_reason": finish_reason,
                }
            ],
        }
        if usage is not None:
            chunk["usage"] = usage
        return chunk

    # Echo the prompt back first if requested.
    if echo_prompt:
        yield f"data: {json.dumps(_make_chunk(echo_prompt, 0, None))}\n\n".encode()

    try:
        async for chunk in chat_stream_generator:
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="ignore")

            for line in chunk.split("\n"):
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    continue

                try:
                    data = json.loads(data_str)
                except (json.JSONDecodeError, TypeError):
                    continue

                choices = data.get("choices", [])
                if not choices:
                    # Final usage-only chunk.
                    if data.get("usage"):
                        usage_chunk = {
                            "id": cmpl_id,
                            "object": "text_completion",
                            "created": created,
                            "model": model,
                            "choices": [],
                            "usage": data["usage"],
                        }
                        yield f"data: {json.dumps(usage_chunk)}\n\n".encode()
                    continue

                for choice in choices:
                    index = choice.get("index", 0)
                    delta = choice.get("delta", {}) or {}
                    text = delta.get("content")
                    finish_reason = choice.get("finish_reason")

                    # Skip role-only / empty keep-alive deltas.
                    if text is None and finish_reason is None:
                        continue

                    yield f"data: {json.dumps(_make_chunk(text or '', index, finish_reason))}\n\n".encode()

    except Exception as e:
        log.error(f"Error in completions stream conversion: {e}")

    yield b"data: [DONE]\n\n"
