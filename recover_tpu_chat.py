#!/usr/bin/env python3
"""
Recover TPU chat from a single OpenRouter log entry (request.json).
Inserts the reconstructed chat back into the Open WebUI database.
"""

import json
import uuid
import time
import sqlite3
import sys

DB_PATH  = "/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data/webui.db"
CHAT_ID  = "660d8fa3-cd79-49a1-a1e0-41064b8cd7ce"
USER_ID  = None   # filled in below from DB
LOG_PATH = "request.json"

# ---------------------------------------------------------------------------

def normalize_content(content):
    """Flatten OpenRouter content (string or list of parts) to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if not isinstance(part, dict):
                parts.append(str(part))
            elif part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif part.get("type") == "tool_use":
                parts.append(f'[tool_call: {part.get("name")}]')
            elif part.get("type") == "tool_result":
                c = part.get("content", "")
                parts.append(f'[tool_result: {normalize_content(c)}]')
        return "\n".join(p for p in parts if p)
    return str(content) if content else ""


def build_owui_history(messages, final_completion):
    """
    Convert a flat list of OpenRouter messages into Open WebUI history format.
    Skips the system prompt (role=system) and tool messages.
    Appends final_completion as the last assistant turn.
    """
    history    = {"messages": {}, "currentId": None}
    parent_id  = None
    ts         = int(time.time())

    for msg in messages:
        role = msg.get("role", "user")

        # System prompt is stored separately in OWUI — skip here
        if role == "system":
            continue
        # Tool result messages are embedded in OWUI assistant content — skip
        if role == "tool":
            continue

        content = normalize_content(msg.get("content", ""))
        msg_id  = str(uuid.uuid4())

        owui_msg = {
            "id":          msg_id,
            "parentId":    parent_id,
            "childrenIds": [],
            "role":        role,
            "content":     content,
            "timestamp":   ts,
            "done":        role == "assistant",
        }

        if parent_id and parent_id in history["messages"]:
            history["messages"][parent_id]["childrenIds"].append(msg_id)

        history["messages"][msg_id] = owui_msg
        history["currentId"]        = msg_id
        parent_id                   = msg_id

    # Append the final model completion as the last assistant message
    if final_completion:
        msg_id  = str(uuid.uuid4())
        owui_msg = {
            "id":          msg_id,
            "parentId":    parent_id,
            "childrenIds": [],
            "role":        "assistant",
            "content":     final_completion,
            "timestamp":   ts,
            "done":        True,
        }
        if parent_id and parent_id in history["messages"]:
            history["messages"][parent_id]["childrenIds"].append(msg_id)
        history["messages"][msg_id] = owui_msg
        history["currentId"]        = msg_id

    return history


def flatten_history(history):
    """Walk the history tree and return a flat ordered messages list."""
    flat = []

    def walk(msg_id):
        msg = history["messages"].get(msg_id)
        if not msg:
            return
        flat.append({"id": msg_id, "role": msg["role"], "content": msg["content"]})
        for child_id in msg.get("childrenIds", []):
            walk(child_id)

    # Find the root (parentId == None)
    for mid, msg in history["messages"].items():
        if msg["parentId"] is None:
            walk(mid)
            break

    return flat


# ---------------------------------------------------------------------------

print(f"Loading {LOG_PATH} ...")
with open(LOG_PATH, "r", encoding="utf-8") as f:
    entry = json.load(f)

# If it's somehow a list, take the first entry
if isinstance(entry, list):
    entry = entry[0]

messages         = entry["inputs"]["messages"]
final_completion = (entry.get("output") or {}).get("completion") or ""
system_prompt    = next((m.get("content","") for m in messages if m.get("role") == "system"), "")
started_at       = entry.get("started_at", "")
model            = (entry.get("inputs") or {}).get("model", "google/gemini-3.1-pro-preview")

print(f"Messages in log  : {len(messages)}")
print(f"System prompt    : {system_prompt[:80]}...")
print(f"First user msg   : {normalize_content(messages[1].get('content',''))[:100]}")
print(f"Final completion : {final_completion[:100]}")

history   = build_owui_history(messages, final_completion)
flat_msgs = flatten_history(history)
print(f"Reconstructed    : {len(history['messages'])} messages")

# ---------------------------------------------------------------------------
# Look up the user_id from the DB (grab from any existing chat)
# ---------------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)

row = conn.execute("SELECT user_id FROM chat LIMIT 1").fetchone()
if not row:
    print("ERROR: Cannot determine user_id — DB has no chats?")
    conn.close()
    sys.exit(1)
user_id = row[0]
print(f"Using user_id    : {user_id}")

# ---------------------------------------------------------------------------
# Build the chat JSON blob
# ---------------------------------------------------------------------------
chat_json = {
    "title":    "🧠 TPU Storage Costs",
    "models":   [model],
    "system":   system_prompt,
    "history":  history,
    "messages": flat_msgs,
    "params":   {},
    "files":    [],
    "timestamp": int(time.time() * 1000),
}

now = int(time.time())

conn.execute("""
    INSERT INTO chat (id, user_id, title, chat, created_at, updated_at, archived, pinned, meta, folder_id)
    VALUES (?, ?, ?, ?, ?, ?, 0, 0, '{}', NULL)
""", (CHAT_ID, user_id, "🧠 TPU Storage Costs", json.dumps(chat_json), now, now))

conn.commit()
conn.close()

print(f"\n✓ Chat inserted: {CHAT_ID}")
print("Refresh Open WebUI to see '🧠 TPU Storage Costs' restored.")
