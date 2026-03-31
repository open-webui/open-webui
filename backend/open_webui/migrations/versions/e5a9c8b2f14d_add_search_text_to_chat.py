"""Add search_text column to chat table for fast full-text search

Revision ID: e5a9c8b2f14d
Revises: 018012973d35
Create Date: 2026-03-31

Replaces the expensive json_each(chat, '$.messages') approach with a
pre-extracted plain-text column so keyword search doesn't JSON-expand
every chat's full message history on every query.
"""

import json
import sqlalchemy as sa
from alembic import op

revision = "e5a9c8b2f14d"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def _extract_content_text(content) -> str:
    """Extract plain text from a message content field (string or multimodal list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return " ".join(parts)
    return ""


def _build_search_text(title: str, chat_data) -> str:
    """Build a flat searchable string from title + all message content."""
    if isinstance(chat_data, str):
        try:
            chat_data = json.loads(chat_data)
        except Exception:
            return (title or "").lower()

    if not isinstance(chat_data, dict):
        return (title or "").lower()

    parts = [title or ""]

    # history.messages is the canonical tree structure
    history = chat_data.get("history") or {}
    history_messages = history.get("messages") if isinstance(history, dict) else None
    if history_messages and isinstance(history_messages, dict):
        for msg in history_messages.values():
            if isinstance(msg, dict):
                content = msg.get("content", "")
                parts.append(_extract_content_text(content))
    elif "messages" in chat_data:
        # Flat messages array fallback
        for msg in chat_data.get("messages") or []:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                parts.append(_extract_content_text(content))

    # Limit to 64KB to keep DB size reasonable
    text = " ".join(parts).lower()
    return text[:65536]


def upgrade():
    op.add_column("chat", sa.Column("search_text", sa.Text(), nullable=True))

    # Backfill existing rows
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, title, chat FROM chat")).fetchall()
    for row in rows:
        try:
            search_text = _build_search_text(row[1], row[2])
            connection.execute(
                sa.text("UPDATE chat SET search_text = :st WHERE id = :id"),
                {"st": search_text, "id": row[0]},
            )
        except Exception:
            pass  # Leave NULL; search will fall back gracefully


def downgrade():
    op.drop_column("chat", "search_text")
