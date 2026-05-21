"""Drop embedded messages from chat JSON for chats that finished migrating
to the chat_message table.

Revision ID: f1a2b3c4d5e6
Revises: e8a7c1d2b3f4
Create Date: 2026-05-21

The previous migration ``c4d8e6f1a902`` introduced ``chat_message`` and
backfilled it from ``chat.chat.history.messages``, but left the embedded
JSON in place so the dual-read shim could fall back to it. Now that we've
confirmed all reads + writes route through ``chat_message`` for migrated
chats, we strip the duplicate copy out of the JSON blob.

What this saves on prod: the JSON column held the entire message history
(median 94 KB, max 133 MB). After this migration the JSON keeps only the
non-message scaffolding (title, models, params, currentId, files, tags,
timestamps) — typically a few KB per chat — and the chat_message table is
the sole source of truth.

VACUUM is intentionally *not* run from inside the migration because it
needs an exclusive DB lock and bricks open sessions. Run it from the shell
after stopping the app:

    sqlite3 webui.db "VACUUM;"

Unmigrated chats (``messages_migrated = 0``) are left untouched.
``_upsert_chat_fts`` already hydrates body content from ``chat_message``
for migrated chats, so FTS coverage stays correct across future title
edits and chat updates.
"""

import sqlalchemy as sa
from alembic import op


revision = "f1a2b3c4d5e6"
down_revision = "e8a7c1d2b3f4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    # Single UPDATE; json_remove tolerates absent paths and returns the input
    # unchanged. The json_valid guard skips any row whose blob is NULL or
    # corrupt — we'd rather leave such rows alone than store a NULL chat
    # column.
    bind.execute(
        sa.text(
            "UPDATE chat "
            "SET chat = json_remove(chat, '$.history.messages', '$.messages') "
            "WHERE messages_migrated = 1 "
            "  AND chat IS NOT NULL "
            "  AND json_valid(chat) = 1"
        )
    )


def downgrade():
    # Not reversible — the data is in chat_message; restoring it to the JSON
    # blob would require re-walking that table per chat. If you need to roll
    # back, restore from the pre-migration backup.
    pass
