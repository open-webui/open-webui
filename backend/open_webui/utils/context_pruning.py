"""
Lightweight deterministic context-pruning for chat messages.

Three strategies, all LLM-free:
  1. Tool output pruning — replace old tool results with placeholders
  2. Tool call deduplication — collapse identical repeated tool calls
  3. Errored tool call purge — drop tool errors after N turns

Runs on every chat (UI + API) before prefix-summarization compaction.
Configured via `chat.context_pruning.*` config keys.
"""

import json
import logging
import re
from typing import Any

from open_webui.models.config import Config

log = logging.getLogger(__name__)


# --- helpers ---

_TOOL_ERROR_PATTERNS = [
    re.compile(r'^Error:', re.IGNORECASE),
    re.compile(r'^Tool error:', re.IGNORECASE),
    re.compile(r'^Error executing tool', re.IGNORECASE),
    re.compile(r'Traceback \(most recent call last\)', re.IGNORECASE),
    re.compile(r'^Exception:', re.IGNORECASE),
]


def _is_likely_tool_error(content: str) -> bool:
    """Heuristic: does this tool result content look like an error?"""
    if not isinstance(content, str) or not content:
        return False
    # Check first 200 chars against patterns
    head = content[:200]
    return any(p.search(head) for p in _TOOL_ERROR_PATTERNS)


def _approx_tokens(text: str) -> int:
    """Quick token approximation (used for placeholder labels only)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _parse_tool_call_key(tool_call: dict) -> tuple[str, str] | None:
    """
    Extract a stable (tool_name, arguments_canonical) key from a tool_call dict.
    Returns None if not a valid tool_call.
    """
    if not isinstance(tool_call, dict):
        return None
    fn = tool_call.get('function') or {}
    name = fn.get('name', '')
    if not name:
        return None
    args = fn.get('arguments', '{}')
    # Normalize args: parse and re-serialize with sorted keys for stable comparison
    try:
        if isinstance(args, str):
            args_parsed = json.loads(args)
        else:
            args_parsed = args
        args_canonical = json.dumps(args_parsed, sort_keys=True, separators=(',', ':'))
    except (json.JSONDecodeError, TypeError):
        args_canonical = str(args)
    return (name, args_canonical)


# --- strategy 1: tool output pruning ---


async def prune_tool_outputs(
    messages: list[dict],
    keep_recent: int = 3,
) -> list[dict]:
    """
    Replace old tool result content with short placeholders, keeping the
    `keep_recent` most recent tool results verbatim.

    Tool messages are messages with role='tool'. They typically contain large
    outputs (web search results, file dumps, knowledge chunks). After a few
    turns these are no longer useful verbatim — a placeholder noting what was
    there is enough for the model to know it had that context.

    Non-mutating; returns a new list.
    """
    if not messages:
        return messages

    # Find indices of all tool messages, in order
    tool_indices = [i for i, m in enumerate(messages) if isinstance(m, dict) and m.get('role') == 'tool']
    if len(tool_indices) <= keep_recent:
        return messages  # nothing to prune

    # Indices to compact (everything except the last `keep_recent`)
    to_compact = set(tool_indices[:-keep_recent] if keep_recent > 0 else tool_indices)

    result = list(messages)
    for i in to_compact:
        msg = result[i]
        original_content = msg.get('content', '')
        original_tokens = _approx_tokens(original_content) if isinstance(original_content, str) else 0
        tool_call_id = msg.get('tool_call_id', '?')
        # Preserve message structure; just replace content
        result[i] = {
            **msg,
            'content': (
                f'[Tool result omitted to save context — was ~{original_tokens} tokens, '
                f'tool_call_id={tool_call_id}. Summary unavailable but the call succeeded.]'
            ),
        }
    return result


# --- strategy 2: tool call deduplication ---


async def dedupe_tool_calls(messages: list[dict]) -> list[dict]:
    """
    Find identical (tool_name, arguments) tool calls in the history. For each
    duplicate set, keep the LATEST call's result verbatim and replace OLDER
    duplicates' results with a placeholder noting they were superseded.

    Only the tool RESULT content is replaced — the assistant tool_call message
    itself is left unchanged (preserves conversation flow). The model can still
    see "I called X with Y args at turn N", but doesn't re-read the same large
    result twice.

    Non-mutating; returns a new list.
    """
    if not messages:
        return messages

    # Walk all assistant messages, collect (tool_name, args) -> list of (msg_idx, tool_call_id)
    # Track first occurrence (oldest) and last occurrence (newest) per key
    occurrences: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for msg_idx, msg in enumerate(messages):
        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
            continue
        tool_calls = msg.get('tool_calls') or []
        for tc in tool_calls:
            key = _parse_tool_call_key(tc)
            if key is None:
                continue
            tc_id = tc.get('id', '')
            occurrences.setdefault(key, []).append((msg_idx, tc_id))

    # For each key with multiple occurrences, mark all but the LATEST for placeholdering
    tool_call_ids_to_compact: set[str] = set()
    for key, occ_list in occurrences.items():
        if len(occ_list) <= 1:
            continue
        # Keep the last (highest msg_idx) verbatim; compact the rest
        occ_list.sort(key=lambda x: x[0])
        for msg_idx, tc_id in occ_list[:-1]:
            tool_call_ids_to_compact.add(tc_id)

    if not tool_call_ids_to_compact:
        return messages

    result = list(messages)
    for i, msg in enumerate(result):
        if isinstance(msg, dict) and msg.get('role') == 'tool' and msg.get('tool_call_id') in tool_call_ids_to_compact:
            result[i] = {
                **msg,
                'content': (
                    f'[Duplicate tool call — same tool and arguments as a later call '
                    f'(tool_call_id={msg.get("tool_call_id", "?")}). Result omitted to save context; '
                    f"the later call's result is preserved verbatim above.]"
                ),
            }
    return result


# --- strategy 3: errored tool call purge ---


async def purge_errored_tool_calls(
    messages: list[dict],
    turn_threshold: int = 2,
) -> list[dict]:
    """
    Drop tool calls whose result indicates an error, once enough turns have
    passed. A "turn" is loosely defined as 2 messages (one user + one
    assistant), so `turn_threshold=2` means purge after 4 subsequent messages.

    The purge removes:
      - The tool result message (role='tool')
      - The corresponding tool_call entry from the assistant message's
        tool_calls array (preserves any text content the assistant produced)

    If removing the tool_call would leave an assistant message with no content
    AND no remaining tool_calls, the entire assistant message is removed.

    The corresponding user message that prompted the tool call is preserved.

    Non-mutating; returns a new list.
    """
    if not messages or turn_threshold < 1:
        return messages

    # Walk all tool messages, find errors and check age
    # Age = number of messages AFTER the tool result
    total = len(messages)
    tool_call_ids_to_purge: set[str] = set()
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict) or msg.get('role') != 'tool':
            continue
        content = msg.get('content', '')
        if not _is_likely_tool_error(content):
            continue
        # Age check: how many messages after this one?
        subsequent = total - i - 1
        # 2 messages per turn (user + assistant)
        if subsequent >= turn_threshold * 2:
            tool_call_ids_to_purge.add(msg.get('tool_call_id', ''))

    if not tool_call_ids_to_purge:
        return messages

    # Build new message list, dropping purged tool messages and stripping
    # the corresponding tool_call entries from assistant messages
    result: list[dict] = []
    for msg in messages:
        if not isinstance(msg, dict):
            result.append(msg)
            continue
        # Drop tool messages whose call_id is being purged
        if msg.get('role') == 'tool' and msg.get('tool_call_id') in tool_call_ids_to_purge:
            continue
        # Strip matching tool_calls from assistant messages
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            remaining_tcs = [tc for tc in (msg.get('tool_calls') or []) if tc.get('id') not in tool_call_ids_to_purge]
            # If all tool_calls were stripped and there's no content, drop the message
            if not remaining_tcs and not msg.get('content'):
                continue
            if len(remaining_tcs) < len(msg.get('tool_calls') or []):
                msg = {**msg, 'tool_calls': remaining_tcs}
        result.append(msg)
    return result


# --- top-level entry point ---


async def prune_messages(messages: list[dict]) -> list[dict]:
    """
    Apply all three pruning strategies in order, gated by config keys.

    Config keys (all default True / enabled):
      - chat.context_pruning.enable               (master switch, default True)
      - chat.context_pruning.tool_output_pruning  (default True)
      - chat.context_pruning.tool_output_keep_recent (default 3)
      - chat.context_pruning.dedupe_tool_calls    (default True)
      - chat.context_pruning.purge_errors         (default True)
      - chat.context_pruning.purge_error_turns    (default 2)

    Non-mutating; returns a new list.
    """
    if not messages:
        return messages

    try:
        # Load config (DB-backed per fork convention — await Config.get)
        enabled = await Config.get('chat.context_pruning.enable', True)
        if not enabled:
            return messages

        if await Config.get('chat.context_pruning.dedupe_tool_calls', True):
            messages = await dedupe_tool_calls(messages)

        if await Config.get('chat.context_pruning.tool_output_pruning', True):
            keep_recent = int(await Config.get('chat.context_pruning.tool_output_keep_recent', 3))
            messages = await prune_tool_outputs(messages, keep_recent=keep_recent)

        if await Config.get('chat.context_pruning.purge_errors', True):
            turn_threshold = int(await Config.get('chat.context_pruning.purge_error_turns', 2))
            messages = await purge_errored_tool_calls(messages, turn_threshold=turn_threshold)
    except Exception as e:
        # Pruning must NEVER break a chat — log and fall through with original messages
        log.error(f'Context pruning failed (continuing with unpruned messages): {e}')
        # Note: 'messages' here is the last pre-error value (may be partially pruned)
        # This is acceptable — partial pruning is better than crashing

    return messages
