"""Add chat_message table + messages_migrated flag on chat.

Revision ID: c4d8e6f1a902
Revises: fa1c3b27e891
Create Date: 2026-05-20

Splits the per-message data out of the embedded `chat.chat` JSON blob into a
dedicated row-per-message `chat_message` table. The motivation: the
production DB has chats with >100 MB of message JSON; every per-message
upsert pays a full read-modify-write of that blob. The new table lets writes
be O(1) per message and reads page-able.

Strategy: dual-read. New rows in `chat_message` are authoritative ONLY when
`chat.messages_migrated = 1`. Until then the JSON blob is still the source
of truth, so unmigrated chats keep working untouched.

The backfill walks `chat` in batches of 50, copying each message into the
new table, and flips `messages_migrated = 1` on success. Per-chat
try/except — one bad blob doesn't block the rest of the migration.

For Postgres/MySQL this migration is a no-op; that path ships in a follow-up.
"""

import json
import sqlalchemy as sa
from alembic import op


revision = "c4d8e6f1a902"
down_revision = "fa1c3b27e891"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "sqlite":
        # Postgres path is a separate migration later.
        return

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_message (
            chat_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            parent_id TEXT,
            role TEXT,
            content TEXT,
            content_is_json INTEGER DEFAULT 0,
            model TEXT,
            timestamp INTEGER,
            sequence INTEGER NOT NULL,
            status_history TEXT,
            meta TEXT,
            PRIMARY KEY (chat_id, message_id),
            FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS chat_message_chat_seq_idx "
        "ON chat_message (chat_id, sequence)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS chat_message_chat_parent_idx "
        "ON chat_message (chat_id, parent_id)"
    )

    # Add messages_migrated column to chat (only if missing).
    inspector = sa.inspect(bind)
    chat_cols = {c["name"] for c in inspector.get_columns("chat")}
    if "messages_migrated" not in chat_cols:
        op.add_column(
            "chat",
            sa.Column(
                "messages_migrated",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    # Cascade delete trigger: when a chat row is deleted, drop its messages
    # too. The FK already declares ON DELETE CASCADE but SQLite only enforces
    # FKs when `PRAGMA foreign_keys = ON` is set on each connection — which
    # isn't guaranteed. A trigger is dialect-portable and free.
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chat_message_cascade_delete
        AFTER DELETE ON chat
        BEGIN
            DELETE FROM chat_message WHERE chat_id = OLD.id;
        END
        """
    )

    # Cursor-based pagination via rowid so failing rows (which stay at
    # messages_migrated=0 inside the try/except below) don't trap the loop
    # and successful rows in earlier batches don't shift the OFFSET window.
    BATCH = 50
    last_rowid = 0
    while True:
        rows = bind.execute(
            sa.text(
                "SELECT id, chat, rowid FROM chat "
                "WHERE messages_migrated = 0 AND rowid > :last "
                "ORDER BY rowid LIMIT :lim"
            ),
            {"lim": BATCH, "last": last_rowid},
        ).fetchall()
        if not rows:
            break

        for row in rows:
            chat_id = row[0]
            chat_data_raw = row[1]
            last_rowid = row[2]
            try:
                if isinstance(chat_data_raw, dict):
                    chat_data = chat_data_raw
                elif chat_data_raw:
                    chat_data = json.loads(chat_data_raw)
                else:
                    chat_data = {}

                history = (
                    chat_data.get("history") or {}
                ) if isinstance(chat_data, dict) else {}
                messages = (
                    history.get("messages") if isinstance(history, dict) else None
                )

                if isinstance(messages, dict):
                    for seq, (mid, msg) in enumerate(messages.items()):
                        if not isinstance(msg, dict):
                            continue
                        content = msg.get("content", "")
                        is_json = 0
                        if not isinstance(content, str):
                            content = json.dumps(content)
                            is_json = 1
                        parent_id = msg.get("parentId")
                        ts = msg.get("timestamp")
                        try:
                            ts_int = int(ts) if ts else None
                        except (TypeError, ValueError):
                            ts_int = None
                        status_history = msg.get("statusHistory")
                        # Keep all extra fields not in the dedicated columns so
                        # round-tripping preserves the original message shape.
                        meta_dict = {
                            k: v
                            for k, v in msg.items()
                            if k
                            not in (
                                "id",
                                "parentId",
                                "role",
                                "content",
                                "model",
                                "timestamp",
                                "statusHistory",
                            )
                        }
                        bind.execute(
                            sa.text(
                                "INSERT OR REPLACE INTO chat_message "
                                "(chat_id, message_id, parent_id, role, "
                                "content, content_is_json, model, timestamp, "
                                "sequence, status_history, meta) "
                                "VALUES (:cid, :mid, :pid, :role, :c, :ij, "
                                ":model, :ts, :seq, :sh, :meta)"
                            ),
                            {
                                "cid": chat_id,
                                "mid": str(mid),
                                "pid": str(parent_id) if parent_id else None,
                                "role": str(msg.get("role", "")),
                                "c": content,
                                "ij": is_json,
                                "model": (
                                    str(msg.get("model", "")) or None
                                ),
                                "ts": ts_int,
                                "seq": seq,
                                "sh": (
                                    json.dumps(status_history)
                                    if status_history
                                    else None
                                ),
                                "meta": (
                                    json.dumps(meta_dict) if meta_dict else None
                                ),
                            },
                        )

                bind.execute(
                    sa.text(
                        "UPDATE chat SET messages_migrated = 1 WHERE id = :id"
                    ),
                    {"id": chat_id},
                )
            except Exception:
                # Skip — this chat stays at messages_migrated=0 and uses the
                # legacy JSON path until a future repair. last_rowid was
                # already advanced above so the loop moves past it.
                pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "sqlite":
        return
    bind.execute(sa.text("DROP TRIGGER IF EXISTS chat_message_cascade_delete"))
    try:
        op.drop_index("chat_message_chat_parent_idx", table_name="chat_message")
    except Exception:
        pass
    try:
        op.drop_index("chat_message_chat_seq_idx", table_name="chat_message")
    except Exception:
        pass
    op.drop_table("chat_message")
    # Intentionally don't drop messages_migrated; preserve forward-compat
    # in case the migration is re-applied later.
