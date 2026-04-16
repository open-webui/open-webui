#!/usr/bin/env python3
"""
Recover a corrupted Open WebUI chat from OpenRouter logs.

Usage:
    python3 recover_tpu_chat.py request.json

It finds the log entry with the most messages whose content matches TPU/storage topics,
reconstructs the Open WebUI history format, and writes the recovered chat back to the DB.
"""

import json
import sys
import uuid
import time
import sqlite3
import re

DB_PATH = "/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data/webui.db"
CHAT_ID  = "660d8fa3-cd79-49a1-a1e0-41064b8cd7ce"

KEYWORDS = ["tpu", "storage", "cost", "tensor", "cloud tpu", "gcs", "pod", "v4", "v5"]

def score_entry(entry):
    """Return how relevant this log entry is to the TPU chat (higher = better)."""
    msgs = []
    inp = entry.get("inputs") or entry.get("input") or {}
    if isinstance(inp, dict):
        msgs = inp.get("messages", [])
    elif isinstance(inp, list):
        msgs = inp

    if not msgs:
        return -1, msgs

    # Count keyword hits across all message content
    all_text = " ".join(
        (m.get("content") or "") if isinstance(m.get("content"), str)
        else " ".join(p.get("text","") for p in m.get("content",[]) if isinstance(p,dict))
        for m in msgs
    ).lower()

    hits = sum(all_text.count(kw) for kw in KEYWORDS)
    # Prefer entries with more messages (more complete history)
    score = hits * 1000 + len(msgs)
    return score, msgs


def build_owui_history(messages, final_completion, final_reasoning):
    """Convert a flat OpenRouter messages list into Open WebUI history format."""
    history = {"messages": {}, "currentId": None}
    parent_id = None

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Normalize content (OpenRouter sometimes sends arrays)
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif part.get("type") == "tool_use":
                        parts.append(f'[tool_call: {part.get("name")}]')
                    elif part.get("type") == "tool_result":
                        parts.append(f'[tool_result: {part.get("content","")}]')
                else:
                    parts.append(str(part))
            content = "\n".join(parts)

        # Skip tool messages — they're embedded in the assistant content in OWUI
        if role == "tool":
            continue

        msg_id = str(uuid.uuid4())
        owui_msg = {
            "id": msg_id,
            "parentId": parent_id,
            "childrenIds": [],
            "role": role,
            "content": content,
            "timestamp": int(time.time()),
            "done": role == "assistant",
        }

        if parent_id and parent_id in history["messages"]:
            history["messages"][parent_id]["childrenIds"].append(msg_id)

        history["messages"][msg_id] = owui_msg
        history["currentId"] = msg_id
        parent_id = msg_id

    # Append the final completion as the last assistant message
    if final_completion:
        msg_id = str(uuid.uuid4())
        owui_msg = {
            "id": msg_id,
            "parentId": parent_id,
            "childrenIds": [],
            "role": "assistant",
            "content": final_completion,
            "timestamp": int(time.time()),
            "done": True,
        }
        if parent_id and parent_id in history["messages"]:
            history["messages"][parent_id]["childrenIds"].append(msg_id)
        history["messages"][msg_id] = owui_msg
        history["currentId"] = msg_id

    return history


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 recover_tpu_chat.py request.json")
        sys.exit(1)

    log_path = sys.argv[1]
    print(f"Loading {log_path} ...")

    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both a single entry and a list of entries
    entries = data if isinstance(data, list) else [data]
    print(f"Found {len(entries)} log entries")

    # Score each entry and pick the best one
    best_score = -1
    best_msgs = []
    best_entry = None

    for entry in entries:
        score, msgs = score_entry(entry)
        if score > best_score:
            best_score = score
            best_msgs = msgs
            best_entry = entry

    if best_score < 0:
        print("ERROR: Could not find any entry with messages. Check the JSON structure.")
        sys.exit(1)

    print(f"Best entry score: {best_score}, messages: {len(best_msgs)}")
    print(f"First user message snippet: {str(best_msgs[0].get('content',''))[:120]}")

    # Get the final completion from this entry's output
    out = best_entry.get("output") or {}
    final_completion = out.get("completion") or out.get("content") or ""
    final_reasoning  = out.get("reasoning") or ""

    history = build_owui_history(best_msgs, final_completion, final_reasoning)
    msg_count = len(history["messages"])
    print(f"Reconstructed history with {msg_count} messages")

    # Build the chat JSON to save
    flat_messages = []
    def walk(msg_id):
        msg = history["messages"].get(msg_id)
        if not msg:
            return
        flat_messages.append({"id": msg_id, "role": msg["role"], "content": msg["content"]})
        for child in msg.get("childrenIds", []):
            walk(child)

    # Find root messages
    for mid, msg in history["messages"].items():
        if msg["parentId"] is None:
            walk(mid)
            break

    # Read current chat record from DB to merge non-history fields
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT chat FROM chat WHERE id = ?", (CHAT_ID,)).fetchone()
    if not row:
        print(f"ERROR: Chat {CHAT_ID} not found in DB")
        conn.close()
        sys.exit(1)

    existing_chat = json.loads(row[0])
    print(f"Existing chat title: {existing_chat.get('title')}")

    # Merge: keep title/models/params from existing, replace history and messages
    new_chat = {
        **existing_chat,
        "history": history,
        "messages": flat_messages,
        "title": "🧠 TPU Storage Costs",  # restore the correct title
    }

    # Write back to DB
    conn.execute(
        "UPDATE chat SET chat = ?, title = ?, updated_at = ? WHERE id = ?",
        (json.dumps(new_chat), "🧠 TPU Storage Costs", int(time.time()), CHAT_ID)
    )
    conn.commit()
    conn.close()

    print(f"\n✓ Chat {CHAT_ID} restored with {msg_count} messages")
    print("Refresh Open WebUI to verify.")


if __name__ == "__main__":
    main()
