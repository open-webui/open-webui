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

This module is also THE one gate that enforces the OpenRouter ``reasoning_details``
uniqueness invariant: every ``rs_*`` id appears in at most one assistant message
in the outbound conversation history. See ``REASONING_DETAILS.md`` (next to this
file) for the full contract, the streaming protocol's quirks, what
OpenRouter tolerates vs. rejects (with empirical curl results), and the historical
bugs the current design replaces.
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


def _dedup_reasoning_against(seen: set, items: Optional[list]) -> Optional[list]:
    """Strip reasoning_details items whose ``id`` is already in ``seen``. Adds the
    surviving items' ids to ``seen`` in place. Items without an ``id`` (e.g.
    ``reasoning.summary`` chunks, which OpenRouter never tags) pass through —
    OpenAI Responses only enforces uniqueness on id-bearing items.

    The single concrete enforcement point for the "no duplicate ``rs_*`` ids in
    the outbound history" invariant. See ``REASONING_DETAILS.md`` §1 (the rule)
    and §6 Bug D (why this lives at module level instead of inside the
    expansion closures).
    """
    if not items:
        return items
    kept = []
    for d in items:
        rid = d.get("id") if isinstance(d, dict) else None
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        kept.append(d)
    return kept


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
    seen_reasoning_ids: Optional[set] = None,
) -> list[dict]:
    """Expand one open-webui assistant message (with structured ``content_blocks``)
    into the per-tool-call-round sequence of API messages OpenAI-compatible upstreams
    expect.

    Each ``rs_*`` reasoning id is emitted at most once across the returned messages.
    Callers passing the same ``seen_reasoning_ids`` set into multiple invocations get
    cross-message dedup as well — required because OpenAI Responses rejects requests
    whose history contains duplicate reasoning item ids with a 500 ("Duplicate item
    found with id rs_<id>").
    """
    api_messages: list[dict] = []
    pending_blocks: list[dict] = []
    emission_index = 0
    if seen_reasoning_ids is None:
        seen_reasoning_ids = set()
    legacy_fallback_consumed = False

    def take_per_round(idx: int) -> Optional[list]:
        if reasoning_details_per_round and idx < len(reasoning_details_per_round):
            return reasoning_details_per_round[idx]
        return None

    def consume_legacy_fallback() -> Optional[list]:
        # The flat `reasoning_details` field on a saved message is a legacy carrier
        # for chats persisted before `reasoning_details_per_round` existed. Hand it
        # to a single emission (the first one that needs reasoning) and let the
        # dedup pass below guarantee no other emission re-emits the same ids.
        nonlocal legacy_fallback_consumed
        if legacy_fallback_consumed or not fallback_reasoning_details:
            return None
        legacy_fallback_consumed = True
        return fallback_reasoning_details

    def flush(tool_calls_block: Optional[dict]):
        nonlocal pending_blocks, emission_index

        text = _assistant_content_from_blocks(pending_blocks)

        tool_calls = (
            tool_calls_block.get("content") or []
            if tool_calls_block is not None
            else []
        )

        if tool_calls_block is not None:
            block_reasoning = tool_calls_block.get("reasoning_details")
            per_round_entry = take_per_round(emission_index)
            chosen_reasoning = block_reasoning or per_round_entry
            # Legacy fallback only fires on emission 0 AND only when both
            # round-specific sources are truly absent (None — not explicit
            # empty []). Explicit empties mean "this round had no reasoning";
            # we honor them. The fallback is the flat carrier from pre-
            # per_round chats and is hand-off-able to a single emission only.
            if (
                block_reasoning is None
                and per_round_entry is None
                and emission_index == 0
            ):
                chosen_reasoning = consume_legacy_fallback()
        else:
            per_round_entry = take_per_round(emission_index)
            chosen_reasoning = per_round_entry
            if per_round_entry is None and emission_index == 0:
                chosen_reasoning = consume_legacy_fallback()

        # Strip any reasoning item whose `id` has already been attached to a
        # prior emission (within this message or — when callers thread one
        # `seen_reasoning_ids` set across the whole conversation — across
        # messages). Duplicate `rs_*` ids cause an upstream 500.
        chosen_reasoning = _dedup_reasoning_against(
            seen_reasoning_ids, chosen_reasoning
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

    # Reasoning-only trailing emission: when content_blocks didn't produce
    # anything (e.g. legacy reasoning-only saves) but per-round reasoning is
    # waiting at the current emission_index, surface it as a content="" message.
    if (
        not api_messages
        and reasoning_details_per_round
        and emission_index < len(reasoning_details_per_round)
    ):
        trailing = _dedup_reasoning_against(
            seen_reasoning_ids, reasoning_details_per_round[emission_index]
        )
        if trailing:
            api_messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "reasoning_details": trailing,
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

    A single ``seen_reasoning_ids`` set is threaded through every assistant expansion
    AND through the legacy passthrough branch. This guarantees each ``rs_*`` reasoning
    id appears in at most one output message — OpenAI Responses rejects history with
    duplicate item ids and OpenRouter surfaces that as a generic 500.
    """
    out: list[dict] = []
    seen_reasoning_ids: set = set()
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
                    seen_reasoning_ids=seen_reasoning_ids,
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
                # Dedup the legacy passthrough reasoning_details against ids
                # already attached upstream in the conversation — same invariant
                # as _expand_assistant's dedup pass, applied here so legacy
                # message shapes don't smuggle duplicates past it.
                rd = cleaned.get("reasoning_details")
                if isinstance(rd, list):
                    kept = _dedup_reasoning_against(seen_reasoning_ids, rd)
                    if kept:
                        cleaned["reasoning_details"] = kept
                    else:
                        cleaned.pop("reasoning_details", None)

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
