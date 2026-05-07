"""Conversion between open-webui internal messages and OpenAI-compatible API messages.

The internal format stores assistant messages with a typed ``content_blocks`` array
(text / reasoning / tool_calls / code_interpreter / ...). The API format uses
OpenAI's flat shape: separate assistant and tool messages, ``tool_calls`` field
on the assistant message, ``tool_call_id`` on the tool message, optional
``reasoning_details`` for reasoning-capable providers.

This module is the single source of truth for that conversion. It is used by the
live agentic tool-call loop and by incoming-payload normalisation in
``generate_chat_completion``. Live and replay produce byte-identical messages
by construction — fixing the prompt-cache drift that the HTML round-trip caused.
"""

from typing import Optional


def _format_code_interpreter(block: dict) -> str:
    attrs = block.get("attributes") or {}
    lang = attrs.get("lang", "")
    code = block.get("content", "") or ""
    output = block.get("output")

    parts = [f"```{lang}", code, "```"]
    if output:
        parts.extend(["", "```output", str(output), "```"])
    return "\n".join(parts)


def _assistant_content_from_blocks(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            text = (block.get("content") or "").strip()
            if text:
                parts.append(text)
        elif btype == "code_interpreter":
            parts.append(_format_code_interpreter(block))
        # reasoning blocks: never enter content (the bytes the cache hashes).
        # The structured form rides on reasoning_details on the assistant message.
    return "\n".join(parts).strip()


def _expand_assistant(
    content_blocks: list[dict],
    reasoning_details_per_round: Optional[list] = None,
    fallback_reasoning_details: Optional[list] = None,
) -> list[dict]:
    api_messages: list[dict] = []
    pending_blocks: list[dict] = []
    emission_index = 0

    def reasoning_for_emission(idx: int, fallback: Optional[list]) -> Optional[list]:
        if reasoning_details_per_round and idx < len(reasoning_details_per_round):
            return reasoning_details_per_round[idx]
        return fallback

    def flush(tool_calls_block: Optional[dict]):
        nonlocal pending_blocks, emission_index

        text = _assistant_content_from_blocks(pending_blocks)

        tool_calls = (
            tool_calls_block.get("content") or []
            if tool_calls_block is not None
            else []
        )

        if tool_calls_block is not None:
            chosen_reasoning = (
                tool_calls_block.get("reasoning_details")
                or reasoning_for_emission(emission_index, None)
            )
        else:
            chosen_reasoning = reasoning_for_emission(
                emission_index, fallback_reasoning_details
            )

        if not text and not tool_calls and not chosen_reasoning:
            pending_blocks = []
            return

        # OpenAI requires content OR tool_calls to be set: content=null is only
        # valid when tool_calls is non-empty. For reasoning-only emissions
        # (preserved so providers like OpenRouter keep the encrypted chain),
        # fall back to "" so the message still validates upstream.
        if tool_calls:
            content_value = text if text else None
        else:
            content_value = text if text else ""

        message: dict = {"role": "assistant", "content": content_value}
        if tool_calls:
            message["tool_calls"] = tool_calls
        if chosen_reasoning:
            message["reasoning_details"] = chosen_reasoning

        api_messages.append(message)
        emission_index += 1
        pending_blocks = []

        if tool_calls:
            for result in tool_calls_block.get("results") or []:
                # Tool results travel as list-of-text-parts so the cache_control
                # transform applied during the live tool loop's last-message marker
                # is shape-stable between live and replay (the same message would
                # otherwise be a string when it isn't the last on replay).
                result_content = result.get("content", "") or ""
                api_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.get("tool_call_id", ""),
                        "content": [{"type": "text", "text": result_content}],
                    }
                )

    for block in content_blocks:
        if block.get("type") == "tool_calls":
            flush(block)
        else:
            pending_blocks.append(block)

    if pending_blocks:
        flush(None)

    if (
        not api_messages
        and reasoning_details_per_round
        and emission_index < len(reasoning_details_per_round)
    ):
        api_messages.append(
            {
                "role": "assistant",
                "content": "",
                "reasoning_details": reasoning_details_per_round[emission_index],
            }
        )

    return api_messages


def blocks_to_api_messages(messages: list[dict]) -> list[dict]:
    """Normalise a list of open-webui internal messages into OpenAI-compatible API messages.

    Assistant messages carrying a non-empty ``content_blocks`` array are expanded into
    one assistant emission per tool-call round (plus a ``tool`` message per result, plus
    a trailing assistant emission for the final response). All other messages pass
    through with ``content_blocks`` stripped — that field is purely an internal carrier
    and has no meaning to the upstream API.
    """
    out: list[dict] = []
    for msg in messages or []:
        if (
            msg.get("role") == "assistant"
            and isinstance(msg.get("content_blocks"), list)
            and msg["content_blocks"]
        ):
            out.extend(
                _expand_assistant(
                    msg["content_blocks"],
                    reasoning_details_per_round=msg.get("reasoning_details_per_round"),
                    fallback_reasoning_details=msg.get("reasoning_details"),
                )
            )
        else:
            # `content_blocks` and `reasoning_details_per_round` are internal carriers;
            # the upstream API does not know about them.
            cleaned = {
                k: v
                for k, v in msg.items()
                if k not in ("content_blocks", "reasoning_details_per_round")
            }
            # Legacy assistant messages (pre-content_blocks migration, or chats
            # whose backfill couldn't recover a text block) may arrive with
            # content=None and no tool_calls — upstream rejects that with
            # "content or tool_calls must be set". Coerce to "" when there's
            # reasoning to preserve, otherwise drop the message entirely.
            if cleaned.get("role") == "assistant":
                content = cleaned.get("content")
                has_content = (
                    (isinstance(content, str) and content != "")
                    or (isinstance(content, list) and len(content) > 0)
                    or (
                        content is not None
                        and not isinstance(content, (str, list))
                    )
                )
                has_tool_calls = bool(cleaned.get("tool_calls"))
                if not has_content and not has_tool_calls:
                    if cleaned.get("reasoning_details"):
                        cleaned["content"] = ""
                    else:
                        continue
            out.append(cleaned)
    return out


def blocks_to_plain_text(content_blocks: Optional[list[dict]]) -> str:
    """Render ``content_blocks`` as plain text / markdown for legacy callers (search,
    title generation, export). Reasoning is included as quoted text. Tool calls collapse
    to a short marker so the projection stays human-readable."""
    parts = []
    for block in content_blocks or []:
        btype = block.get("type")
        if btype == "text":
            text = block.get("content") or ""
            if text:
                parts.append(text)
        elif btype == "reasoning":
            reasoning = block.get("content") or ""
            if reasoning:
                parts.append("\n".join(f"> {line}" for line in reasoning.splitlines()))
        elif btype == "tool_calls":
            for call in block.get("content") or []:
                name = (call.get("function") or {}).get("name") or "tool"
                parts.append(f"[Tool: {name}]")
        elif btype == "code_interpreter":
            parts.append(_format_code_interpreter(block))
    return "\n\n".join(parts).strip()
