"""Concurrent-safe chat history merge utilities for realtime voice sessions.

Provides merge logic for the read-merge-write pattern used by chat_sync.py.
Lives in realtime/ (not stock chats.py) per PR architecture rules.
"""

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


def merge_message_children(existing: list, incoming: list) -> list:
    """Union-merge childrenIds arrays without duplicates, preserving order."""
    merged: list[str] = []
    for child_id in [*(existing or []), *(incoming or [])]:
        if isinstance(child_id, str) and child_id and child_id not in merged:
            merged.append(child_id)
    return merged


def merge_chat_message(existing: dict, incoming: dict) -> dict:
    """Merge two message dicts, handling childrenIds and content conflicts."""
    if not isinstance(existing, dict):
        return incoming
    if not isinstance(incoming, dict):
        return existing

    merged = {**existing, **incoming}

    # Union-merge childrenIds
    if "childrenIds" in existing or "childrenIds" in incoming:
        merged["childrenIds"] = merge_message_children(
            existing.get("childrenIds", []),
            incoming.get("childrenIds", []),
        )

    # Content conflict: done-flag wins, otherwise longest-prefix wins
    existing_content = existing.get("content")
    incoming_content = incoming.get("content")
    if isinstance(existing_content, str) and isinstance(incoming_content, str):
        if existing.get("done") and not incoming.get("done"):
            merged["content"] = existing_content
            merged["done"] = True
        elif incoming.get("done") and not existing.get("done"):
            merged["content"] = incoming_content
            merged["done"] = True
        elif existing_content.startswith(incoming_content):
            merged["content"] = existing_content
        elif incoming_content.startswith(existing_content):
            merged["content"] = incoming_content

    return merged


def merge_chat_payload(existing_chat: dict, incoming_chat: dict) -> dict:
    """Merge incoming chat changes into existing chat state.

    Handles:
    - Message-level merge with childrenIds union and content conflict resolution
    - deletedMessageIds protocol for orphan cleanup
    - currentId reconciliation
    """
    merged_chat = {**existing_chat, **incoming_chat}

    existing_history = existing_chat.get("history")
    incoming_history = incoming_chat.get("history")
    if not isinstance(existing_history, dict) or not isinstance(incoming_history, dict):
        return merged_chat

    merged_history = {**existing_history, **incoming_history}
    existing_messages = existing_history.get("messages", {}) or {}
    incoming_messages = incoming_history.get("messages", {}) or {}

    # Handle deletedMessageIds protocol
    deleted_message_ids = {
        mid
        for mid in incoming_history.get("deletedMessageIds", []) or []
        if isinstance(mid, str) and mid
    }

    if isinstance(existing_messages, dict) and isinstance(incoming_messages, dict):
        merged_messages = dict(existing_messages)

        # Remove deleted messages
        for mid in deleted_message_ids:
            merged_messages.pop(mid, None)

        # Merge incoming messages
        for mid, incoming_message in incoming_messages.items():
            merged_messages[mid] = merge_chat_message(
                existing_messages.get(mid, {}),
                incoming_message,
            )

        # Filter deleted IDs from childrenIds of remaining messages
        if deleted_message_ids:
            for message in merged_messages.values():
                if isinstance(message, dict) and isinstance(message.get("childrenIds"), list):
                    message["childrenIds"] = [
                        cid for cid in message["childrenIds"]
                        if isinstance(cid, str) and cid not in deleted_message_ids
                    ]

        merged_history["messages"] = merged_messages

        # Reconcile currentId
        existing_current = existing_history.get("currentId")
        incoming_current = incoming_history.get("currentId")
        if incoming_current and incoming_current in merged_messages:
            merged_history["currentId"] = incoming_current
        elif existing_current and existing_current in merged_messages:
            merged_history["currentId"] = existing_current
        else:
            merged_history.pop("currentId", None)

    # Clean up protocol field
    merged_history.pop("deletedMessageIds", None)
    merged_chat["history"] = merged_history
    return merged_chat


def build_realtime_delete_patch(
    message_ids: list[str],
    parent_id: Optional[str] = None,
) -> dict:
    """Build a chat history patch that signals message deletion via the merge protocol.

    The returned dict can be passed to Chats.update_chat_by_id() after
    merge_chat_payload() processes it.
    """
    patch: dict[str, Any] = {
        "history": {
            "deletedMessageIds": [mid for mid in message_ids if mid],
        }
    }
    if parent_id:
        patch["history"]["currentId"] = parent_id
    return patch
