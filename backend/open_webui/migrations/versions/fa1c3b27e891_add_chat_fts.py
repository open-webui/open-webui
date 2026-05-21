"""Add FTS5 chat search

Revision ID: fa1c3b27e891
Revises: a7f2d8b4c901, 10vr9xyets5m
Create Date: 2026-05-20

Adds three FTS5 virtual tables for SQLite-based full-text chat search:
  chat_fts      - chat-level (title, body), porter+unicode61 tokenizer
  message_fts   - per-message rows, drives snippets and match counts
  chat_fts_tri  - trigram tokenizer for fuzzy / CJK fallback

INSERT/UPDATE writes happen in app code (models/chats.py) so JSON unpack
is centralised. A SQLite trigger handles DELETE cascade.

Backfills existing chats in batches of 500.

For Postgres/MySQL this migration is a no-op; the Postgres branch will
ship in a follow-up using tsvector + GIN.
"""

import json
import sqlalchemy as sa
from alembic import op

revision = "fa1c3b27e891"
down_revision = ("a7f2d8b4c901", "10vr9xyets5m")
branch_labels = None
depends_on = None


PRIMARY_TOKENIZER = "porter unicode61 remove_diacritics 2 tokenchars '_-'"


def _extract_content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return ""


def _chat_body_text(title, chat_data):
    if isinstance(chat_data, str):
        try:
            chat_data = json.loads(chat_data)
        except Exception:
            return title or ""
    if not isinstance(chat_data, dict):
        return title or ""
    parts = [title or ""]
    history = chat_data.get("history") or {}
    history_messages = history.get("messages") if isinstance(history, dict) else None
    if history_messages and isinstance(history_messages, dict):
        for msg in history_messages.values():
            if isinstance(msg, dict):
                parts.append(_extract_content_text(msg.get("content", "")))
    elif "messages" in chat_data:
        for msg in chat_data.get("messages") or []:
            if isinstance(msg, dict):
                parts.append(_extract_content_text(msg.get("content", "")))
    return " ".join(parts)[:65536]


def _iter_messages(chat_data):
    if isinstance(chat_data, str):
        try:
            chat_data = json.loads(chat_data)
        except Exception:
            return
    if not isinstance(chat_data, dict):
        return
    history = chat_data.get("history") or {}
    history_messages = history.get("messages") if isinstance(history, dict) else None
    if history_messages and isinstance(history_messages, dict):
        for mid, msg in history_messages.items():
            if isinstance(msg, dict):
                yield (
                    str(mid),
                    str(msg.get("role", "")),
                    _extract_content_text(msg.get("content", "")),
                )
    elif "messages" in chat_data:
        for idx, msg in enumerate(chat_data.get("messages") or []):
            if isinstance(msg, dict):
                yield (
                    str(msg.get("id", f"_{idx}")),
                    str(msg.get("role", "")),
                    _extract_content_text(msg.get("content", "")),
                )


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "sqlite":
        return

    bind.execute(sa.text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chat_fts USING fts5("
        "  id UNINDEXED,"
        "  title,"
        "  body,"
        f" tokenize = \"{PRIMARY_TOKENIZER}\","
        "  prefix = '2 3 4'"
        ")"
    ))
    bind.execute(sa.text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS message_fts USING fts5("
        "  chat_id UNINDEXED,"
        "  message_id UNINDEXED,"
        "  role UNINDEXED,"
        "  content,"
        f" tokenize = \"{PRIMARY_TOKENIZER}\","
        "  prefix = '2 3 4'"
        ")"
    ))
    bind.execute(sa.text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chat_fts_tri USING fts5("
        "  id UNINDEXED,"
        "  content,"
        "  tokenize = 'trigram'"
        ")"
    ))

    bind.execute(sa.text(
        "CREATE TRIGGER IF NOT EXISTS chat_fts_delete AFTER DELETE ON chat "
        "BEGIN "
        "  DELETE FROM chat_fts WHERE id = OLD.id; "
        "  DELETE FROM message_fts WHERE chat_id = OLD.id; "
        "  DELETE FROM chat_fts_tri WHERE id = OLD.id; "
        "END"
    ))

    BATCH = 500
    offset = 0
    while True:
        rows = bind.execute(sa.text(
            "SELECT id, title, chat FROM chat ORDER BY rowid LIMIT :lim OFFSET :off"
        ), {"lim": BATCH, "off": offset}).fetchall()
        if not rows:
            break

        for row in rows:
            chat_id = row[0]
            title = row[1] or ""
            chat_data = row[2]

            try:
                body = _chat_body_text(title, chat_data)

                bind.execute(sa.text("DELETE FROM chat_fts WHERE id = :id"), {"id": chat_id})
                bind.execute(sa.text(
                    "INSERT INTO chat_fts (id, title, body) VALUES (:id, :t, :b)"
                ), {"id": chat_id, "t": title, "b": body})

                bind.execute(sa.text("DELETE FROM message_fts WHERE chat_id = :id"), {"id": chat_id})
                for mid, role, content in _iter_messages(chat_data):
                    if not content:
                        continue
                    bind.execute(sa.text(
                        "INSERT INTO message_fts (chat_id, message_id, role, content) "
                        "VALUES (:cid, :mid, :role, :content)"
                    ), {"cid": chat_id, "mid": mid, "role": role, "content": content[:65536]})

                bind.execute(sa.text("DELETE FROM chat_fts_tri WHERE id = :id"), {"id": chat_id})
                bind.execute(sa.text(
                    "INSERT INTO chat_fts_tri (id, content) VALUES (:id, :c)"
                ), {"id": chat_id, "c": body})
            except Exception:
                # Skip rows that fail to parse; updates will heal them later.
                pass

        offset += BATCH


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "sqlite":
        return
    bind.execute(sa.text("DROP TRIGGER IF EXISTS chat_fts_delete"))
    bind.execute(sa.text("DROP TABLE IF EXISTS chat_fts"))
    bind.execute(sa.text("DROP TABLE IF EXISTS message_fts"))
    bind.execute(sa.text("DROP TABLE IF EXISTS chat_fts_tri"))
