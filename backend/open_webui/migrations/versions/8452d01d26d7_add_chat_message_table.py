"""Add chat_message table

Revision ID: 8452d01d26d7
Revises: 374d2f66af06
Create Date: 2026-02-01 04:00:00.000000

"""

import time
import json
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

log = logging.getLogger(__name__)

revision: str = "8452d01d26d7"
down_revision: Union[str, None] = "374d2f66af06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create table
    op.create_table(
        "chat_message",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("chat_id", sa.Text(), nullable=False, index=True),
        sa.Column("user_id", sa.Text(), index=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True, index=True),
        sa.Column("files", sa.JSON(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("embeds", sa.JSON(), nullable=True),
        sa.Column("done", sa.Boolean(), default=True),
        sa.Column("status_history", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("usage", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), index=True),
        sa.Column("updated_at", sa.BigInteger()),
        sa.ForeignKeyConstraint(["chat_id"], ["chat.id"], ondelete="CASCADE"),
    )

    # Create composite indexes
    op.create_index(
        "chat_message_chat_parent_idx", "chat_message", ["chat_id", "parent_id"]
    )
    op.create_index(
        "chat_message_model_created_idx", "chat_message", ["model_id", "created_at"]
    )
    op.create_index(
        "chat_message_user_created_idx", "chat_message", ["user_id", "created_at"]
    )

    # Step 2: Backfill from existing chats
    conn = op.get_bind()

    chat_table = sa.table(
        "chat",
        sa.column("id", sa.Text()),
        sa.column("user_id", sa.Text()),
        sa.column("chat", sa.JSON()),
    )

    chat_message_table = sa.table(
        "chat_message",
        sa.column("id", sa.Text()),
        sa.column("chat_id", sa.Text()),
        sa.column("user_id", sa.Text()),
        sa.column("role", sa.Text()),
        sa.column("parent_id", sa.Text()),
        sa.column("content", sa.JSON()),
        sa.column("output", sa.JSON()),
        sa.column("model_id", sa.Text()),
        sa.column("files", sa.JSON()),
        sa.column("sources", sa.JSON()),
        sa.column("embeds", sa.JSON()),
        sa.column("done", sa.Boolean()),
        sa.column("status_history", sa.JSON()),
        sa.column("error", sa.JSON()),
        sa.column("usage", sa.JSON()),
        sa.column("created_at", sa.BigInteger()),
        sa.column("updated_at", sa.BigInteger()),
    )

    # Fetch all chats (excluding shared chats which have user_id starting with 'shared-')
    chats = conn.execute(
        sa.select(chat_table.c.id, chat_table.c.user_id, chat_table.c.chat).where(
            ~chat_table.c.user_id.like("shared-%")
        )
    ).fetchall()

    now = int(time.time())
    messages_inserted = 0
    messages_failed = 0

    for chat_row in chats:
        chat_id = chat_row[0]
        user_id = chat_row[1]
        chat_data = chat_row[2]

        if not chat_data:
            continue

        # Handle both string and dict chat data
        if isinstance(chat_data, str):
            try:
                chat_data = json.loads(chat_data)
            except Exception:
                continue

        history = chat_data.get("history", {})
        messages = history.get("messages", {})

        for message_id, message in messages.items():
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            if not role:
                continue

            timestamp = message.get("timestamp", now)

            # Normalize timestamp: convert ms to seconds, validate range
            if timestamp > 10_000_000_000:
                timestamp = timestamp // 1000
            # Must be after 2020 and not too far in the future
            if timestamp < 1577836800 or timestamp > now + 86400:
                timestamp = now

            # Use savepoint to allow individual insert failures without aborting transaction
            savepoint = conn.begin_nested()
            try:
                conn.execute(
                    sa.insert(chat_message_table).values(
                        id=f"{chat_id}-{message_id}",
                        chat_id=chat_id,
                        user_id=user_id,
                        role=role,
                        parent_id=message.get("parentId"),
                        content=message.get("content"),
                        output=message.get("output"),
                        model_id=message.get("model"),
                        files=message.get("files"),
                        sources=message.get("sources"),
                        embeds=message.get("embeds"),
                        done=message.get("done", True),
                        status_history=message.get("statusHistory"),
                        error=message.get("error"),
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
                savepoint.commit()
                messages_inserted += 1
            except Exception as e:
                savepoint.rollback()
                messages_failed += 1
                log.warning(f"Failed to insert message {message_id}: {e}")
                continue

    log.info(
        f"Backfilled {messages_inserted} messages into chat_message table ({messages_failed} failed)"
    )


def downgrade() -> None:
    op.drop_index("chat_message_user_created_idx", table_name="chat_message")
    op.drop_index("chat_message_model_created_idx", table_name="chat_message")
    op.drop_index("chat_message_chat_parent_idx", table_name="chat_message")
    op.drop_table("chat_message")
