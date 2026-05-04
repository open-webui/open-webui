"""Backfill content_blocks on assistant messages from legacy HTML content

Revision ID: a7f2d8b4c901
Revises: e5a9c8b2f14d
Create Date: 2026-05-03

Walks every chat in the DB and, for each assistant message that has a legacy
HTML ``content`` string but no structured ``content_blocks``, parses the
``<details type="reasoning|tool_calls|code_interpreter">`` blocks out of the
content and rebuilds them as a typed ``content_blocks`` array.

Why: replay (next-turn API request) historically reconstructed tool-call
messages by parsing HTML — and that parser drifted from the live-loop
producer, which destroyed Anthropic prompt caching after every tool-using
turn. Persisting structured blocks moves replay onto the same data the live
loop already speaks, so live and replay produce byte-identical messages.

Idempotent (skips messages with content_blocks already), failure-tolerant
(per-message try/except, malformed messages get a lossy text-only fallback).
"""

import html
import json
import logging
import re
from typing import Optional

import sqlalchemy as sa
from alembic import op


revision = "a7f2d8b4c901"
down_revision = "e5a9c8b2f14d"
branch_labels = None
depends_on = None


log = logging.getLogger("alembic.runtime.migration.content_blocks_backfill")


_DETAILS_RE = re.compile(
    r'<details\s+type="(?P<type>[^"]+)"(?P<attrs>[^>]*)>(?P<inner>.*?)</details>',
    re.DOTALL | re.IGNORECASE,
)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_SUMMARY_RE = re.compile(r"<summary>.*?</summary>\s*", re.DOTALL | re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)


def _decode_attr_payload(raw: str):
    """HTML-decode + JSON-decode the value of an attribute that the live loop
    encoded via ``html.escape(json.dumps(value))``. Mirrors the frontend's
    ``normalizeToolCallArguments`` / ``normalizeToolResultContent``."""
    if raw is None:
        return ""
    decoded = html.unescape(raw)
    try:
        parsed = json.loads(decoded)
    except Exception:
        return decoded
    if isinstance(parsed, str):
        return parsed
    return json.dumps(parsed)


def _parse_attrs(attrs_str: str) -> dict:
    out: dict = {}
    if not attrs_str:
        return out
    for key, value in _ATTR_RE.findall(attrs_str):
        out[key] = value
    return out


def _strip_quoted(text: str) -> str:
    """Strip the ``> `` markdown blockquote prefix used by the reasoning serializer."""
    lines = []
    for line in text.splitlines():
        if line.startswith("> "):
            lines.append(line[2:])
        elif line.startswith(">"):
            lines.append(line[1:])
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def _is_meaningful(text: str) -> bool:
    return bool(text and text.strip())


def _build_text_block(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    return {"type": "text", "content": text}


def _build_reasoning_block(attrs: dict, inner: str) -> dict:
    inner_no_summary = _SUMMARY_RE.sub("", inner)
    reasoning = _strip_quoted(inner_no_summary)
    block = {"type": "reasoning", "content": reasoning}
    duration = attrs.get("duration")
    if duration is not None:
        try:
            block["duration"] = int(duration)
        except (TypeError, ValueError):
            pass
    return block


def _build_code_interpreter_block(attrs: dict, inner: str) -> dict:
    inner_no_summary = _SUMMARY_RE.sub("", inner).strip()
    lang = ""
    code = inner_no_summary
    fence_match = _CODE_FENCE_RE.search(inner_no_summary)
    if fence_match:
        lang = (fence_match.group(1) or "").strip()
        code = fence_match.group(2).rstrip()
    output_raw = attrs.get("output")
    output = _decode_attr_payload(output_raw) if output_raw else None
    block = {"type": "code_interpreter", "content": code, "attributes": {"lang": lang}}
    if output:
        block["output"] = output
    return block


def _build_tool_call_record(attrs: dict) -> dict:
    return {
        "id": attrs.get("id", ""),
        "type": "function",
        "function": {
            "name": attrs.get("name", ""),
            "arguments": _decode_attr_payload(attrs.get("arguments", "")),
        },
    }


def _build_tool_result_record(attrs: dict) -> dict:
    record: dict = {
        "tool_call_id": attrs.get("id", ""),
        "content": _decode_attr_payload(attrs.get("result", "")),
    }
    files_raw = attrs.get("files")
    if files_raw:
        try:
            decoded = json.loads(html.unescape(files_raw))
            if decoded:
                record["files"] = decoded
        except Exception:
            pass
    embeds_raw = attrs.get("embeds")
    if embeds_raw:
        try:
            decoded = json.loads(html.unescape(embeds_raw))
            if decoded:
                record["embeds"] = decoded
        except Exception:
            pass
    return record


def _parse_content_to_blocks(
    content: str, reasoning_details_per_round: Optional[list]
) -> list:
    """Parse a legacy HTML-content string into typed content_blocks, mirroring the
    semantics of expandPreservedToolContextMessage from the frontend."""
    if not isinstance(content, str) or not content:
        return []

    blocks: list[dict] = []
    cursor = 0

    pending_tool_calls: list[dict] = []  # parallel calls waiting to be flushed
    pending_tool_results: list[dict] = []
    last_match_was_tool_call = False
    text_since_last_tool_call: list[str] = []

    def flush_tool_calls(round_index_holder: list):
        if not pending_tool_calls:
            return
        block = {
            "type": "tool_calls",
            "content": list(pending_tool_calls),
            "results": list(pending_tool_results),
        }
        idx = round_index_holder[0]
        if (
            reasoning_details_per_round
            and 0 <= idx < len(reasoning_details_per_round)
        ):
            block["reasoning_details"] = reasoning_details_per_round[idx]
        blocks.append(block)
        pending_tool_calls.clear()
        pending_tool_results.clear()
        round_index_holder[0] += 1

    round_index_holder = [0]

    def flush_text():
        nonlocal text_since_last_tool_call
        text = "".join(text_since_last_tool_call)
        text_since_last_tool_call = []
        block = _build_text_block(text)
        if block is not None:
            blocks.append(block)

    for m in _DETAILS_RE.finditer(content):
        text_before = content[cursor : m.start()]

        if last_match_was_tool_call and not _is_meaningful(text_before):
            # Adjacent tool_calls (no meaningful text between) belong to the
            # same round → keep them in pending_*; do not flush.
            pass
        else:
            if pending_tool_calls:
                flush_tool_calls(round_index_holder)
            text_since_last_tool_call.append(text_before)
            flush_text()

        block_type = (m.group("type") or "").lower()
        attrs = _parse_attrs(m.group("attrs") or "")
        inner = m.group("inner") or ""

        if block_type == "reasoning":
            blocks.append(_build_reasoning_block(attrs, inner))
            last_match_was_tool_call = False
        elif block_type == "code_interpreter":
            blocks.append(_build_code_interpreter_block(attrs, inner))
            last_match_was_tool_call = False
        elif block_type == "tool_calls" and attrs.get("done", "").lower() == "true":
            pending_tool_calls.append(_build_tool_call_record(attrs))
            pending_tool_results.append(_build_tool_result_record(attrs))
            last_match_was_tool_call = True
        else:
            last_match_was_tool_call = False

        cursor = m.end()

    trailing_text = content[cursor:]
    if pending_tool_calls and not _is_meaningful(trailing_text):
        flush_tool_calls(round_index_holder)
    elif pending_tool_calls:
        flush_tool_calls(round_index_holder)
        text_since_last_tool_call.append(trailing_text)
        flush_text()
    else:
        text_since_last_tool_call.append(trailing_text)
        flush_text()

    return blocks


def _migrate_message(message: dict) -> bool:
    """Returns True if the message was modified."""
    if not isinstance(message, dict):
        return False
    if message.get("role") != "assistant":
        return False
    if isinstance(message.get("content_blocks"), list):
        return False  # already migrated

    content = message.get("content")
    if not isinstance(content, str):
        return False

    reasoning_details_per_round = message.get("reasoning_details_per_round")
    try:
        blocks = _parse_content_to_blocks(content, reasoning_details_per_round)
    except Exception as exc:
        log.warning("content_blocks parse failed for message; using fallback: %s", exc)
        plain = re.sub(r"<[^>]+>", "", content).strip()
        blocks = [{"type": "text", "content": plain}] if plain else []

    message["content_blocks"] = blocks
    return True


def _migrate_chat(chat_data) -> Optional[dict]:
    """Migrate a single chat record's history.messages. Returns the new chat dict
    (with content_blocks added) if anything changed, else None."""
    if isinstance(chat_data, str):
        try:
            chat_data = json.loads(chat_data)
        except Exception:
            return None

    if not isinstance(chat_data, dict):
        return None

    history = chat_data.get("history")
    if not isinstance(history, dict):
        return None

    messages = history.get("messages")
    if not isinstance(messages, dict):
        return None

    changed = False
    for msg in messages.values():
        if _migrate_message(msg):
            changed = True

    if not changed:
        return None

    return chat_data


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, chat FROM chat")).fetchall()
    migrated = 0
    skipped = 0
    failed = 0

    for row in rows:
        try:
            new_chat = _migrate_chat(row[1])
            if new_chat is None:
                skipped += 1
                continue
            connection.execute(
                sa.text("UPDATE chat SET chat = :chat WHERE id = :id"),
                {"chat": json.dumps(new_chat), "id": row[0]},
            )
            migrated += 1
        except Exception as exc:
            failed += 1
            log.warning("content_blocks migration failed for chat %s: %s", row[0], exc)

    log.info(
        "content_blocks backfill complete: migrated=%d skipped=%d failed=%d",
        migrated,
        skipped,
        failed,
    )


def downgrade() -> None:
    """Removes the ``content_blocks`` field from every assistant message. Lossy by
    design — the live loop persists content_blocks going forward; rolling back means
    accepting that the next turn after a tool call will partial-cache again until a
    fresh response replays into HTML."""
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, chat FROM chat")).fetchall()
    for row in rows:
        try:
            chat_data = row[1]
            if isinstance(chat_data, str):
                chat_data = json.loads(chat_data)
            if not isinstance(chat_data, dict):
                continue
            history = chat_data.get("history") or {}
            messages = history.get("messages") if isinstance(history, dict) else None
            if not isinstance(messages, dict):
                continue
            changed = False
            for msg in messages.values():
                if isinstance(msg, dict) and "content_blocks" in msg:
                    del msg["content_blocks"]
                    changed = True
            if changed:
                connection.execute(
                    sa.text("UPDATE chat SET chat = :chat WHERE id = :id"),
                    {"chat": json.dumps(chat_data), "id": row[0]},
                )
        except Exception:
            pass
