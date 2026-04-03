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

revision: str = '8452d01d26d7'
down_revision: Union[str, None] = '374d2f66af06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BATCH_SIZE = 5000
CHAT_PAGE_SIZE = 100


def _parse_chat_messages(chat_id, user_id, chat_data, now):
    """Extract and normalize messages from a chat row's JSON data."""
    if not chat_data:
        return []

    if isinstance(chat_data, str):
        try:
            chat_data = json.loads(chat_data)
        except Exception:
            return []

    history = chat_data.get('history', {})
    if not isinstance(history, dict):
        return []

    messages = history.get('messages', {})
    if not isinstance(messages, dict):
        return []

    result = []
    for message_id, message in messages.items():
        if not isinstance(message, dict):
            continue

        role = message.get('role')
        if not role:
            continue

        timestamp = message.get('timestamp', now)
        try:
            timestamp = int(float(timestamp))
        except Exception:
            timestamp = now

        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000
        if timestamp < 1577836800 or timestamp > now + 86400:
            timestamp = now

        result.append({
            'id': f'{chat_id}-{message_id}',
            'chat_id': chat_id,
            'user_id': user_id,
            'role': role,
            'parent_id': message.get('parentId'),
            'content': message.get('content'),
            'output': message.get('output'),
            'model_id': message.get('model'),
            'files': message.get('files'),
            'sources': message.get('sources'),
            'embeds': message.get('embeds'),
            'done': message.get('done', True),
            'status_history': message.get('statusHistory'),
            'error': message.get('error'),
            'usage': message.get('usage'),
            'created_at': timestamp,
            'updated_at': timestamp,
        })

    return result


def _flush_batch(conn, table, batch):
    """Insert a batch with savepoint fallback (for SQLite/default path)."""
    savepoint = conn.begin_nested()
    try:
        conn.execute(sa.insert(table), batch)
        savepoint.commit()
        return len(batch), 0
    except Exception:
        savepoint.rollback()
        inserted = 0
        failed = 0
        for msg in batch:
            sp = conn.begin_nested()
            try:
                conn.execute(sa.insert(table).values(**msg))
                sp.commit()
                inserted += 1
            except Exception as e:
                sp.rollback()
                failed += 1
                log.warning(f'Failed to insert message {msg["id"]}: {e}')
        return inserted, failed


def _flush_batch_pg(conn, table, batch):
    """Insert a batch with ON CONFLICT DO NOTHING (PostgreSQL path)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    try:
        stmt = pg_insert(table).values(batch).on_conflict_do_nothing(
            index_elements=['id']
        )
        result = conn.execute(stmt)
        return result.rowcount, len(batch) - result.rowcount
    except Exception:
        inserted = 0
        failed = 0
        for msg in batch:
            try:
                stmt = pg_insert(table).values(**msg).on_conflict_do_nothing(
                    index_elements=['id']
                )
                result = conn.execute(stmt)
                inserted += result.rowcount
            except Exception as e:
                failed += 1
                log.warning(f'Failed to insert message {msg["id"]}: {e}')
        return inserted, failed


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        _upgrade_postgresql()
    else:
        _upgrade_default()


def _upgrade_default() -> None:
    """Original migration path for SQLite and other backends."""
    op.create_table(
        'chat_message',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('chat_id', sa.Text(), nullable=False, index=True),
        sa.Column('user_id', sa.Text(), index=True),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Text(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('output', sa.JSON(), nullable=True),
        sa.Column('model_id', sa.Text(), nullable=True, index=True),
        sa.Column('files', sa.JSON(), nullable=True),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('embeds', sa.JSON(), nullable=True),
        sa.Column('done', sa.Boolean(), default=True),
        sa.Column('status_history', sa.JSON(), nullable=True),
        sa.Column('error', sa.JSON(), nullable=True),
        sa.Column('usage', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), index=True),
        sa.Column('updated_at', sa.BigInteger()),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
    )

    op.create_index(
        'chat_message_chat_parent_idx', 'chat_message', ['chat_id', 'parent_id']
    )
    op.create_index(
        'chat_message_model_created_idx',
        'chat_message',
        ['model_id', 'created_at'],
    )
    op.create_index(
        'chat_message_user_created_idx',
        'chat_message',
        ['user_id', 'created_at'],
    )

    conn = op.get_bind()
    chat_table = sa.table(
        'chat',
        sa.column('id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('chat', sa.JSON()),
    )
    chat_message_table = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('role', sa.Text()),
        sa.column('parent_id', sa.Text()),
        sa.column('content', sa.JSON()),
        sa.column('output', sa.JSON()),
        sa.column('model_id', sa.Text()),
        sa.column('files', sa.JSON()),
        sa.column('sources', sa.JSON()),
        sa.column('embeds', sa.JSON()),
        sa.column('done', sa.Boolean()),
        sa.column('status_history', sa.JSON()),
        sa.column('error', sa.JSON()),
        sa.column('usage', sa.JSON()),
        sa.column('created_at', sa.BigInteger()),
        sa.column('updated_at', sa.BigInteger()),
    )

    result = conn.execute(
        sa.select(chat_table.c.id, chat_table.c.user_id, chat_table.c.chat)
        .where(~chat_table.c.user_id.like('shared-%'))
        .execution_options(yield_per=1000, stream_results=True)
    )

    now = int(time.time())
    messages_batch = []
    total_inserted = 0
    total_failed = 0

    for chat_row in result:
        for msg in _parse_chat_messages(chat_row[0], chat_row[1], chat_row[2], now):
            messages_batch.append(msg)
            if len(messages_batch) >= BATCH_SIZE:
                inserted, failed = _flush_batch(
                    conn, chat_message_table, messages_batch
                )
                total_inserted += inserted
                total_failed += failed
                if total_inserted % 50000 < BATCH_SIZE:
                    log.info(
                        f'Migration progress: {total_inserted} messages inserted...'
                    )
                messages_batch.clear()

    if messages_batch:
        inserted, failed = _flush_batch(conn, chat_message_table, messages_batch)
        total_inserted += inserted
        total_failed += failed

    log.info(
        f'Backfilled {total_inserted} messages into chat_message table'
        f' ({total_failed} failed)'
    )


def _upgrade_postgresql() -> None:
    """
    PostgreSQL-optimized migration following bulk-load best practices:
    1. Create table with PK only (no secondary indexes, no FK)
    2. Backfill using keyset pagination with per-chunk commits
    3. Create indexes after backfill (bulk construction)
    4. Add FK as NOT VALID, then VALIDATE CONSTRAINT

    This avoids:
    - Unbounded WAL growth from single-transaction backfill
    - Per-row index maintenance write amplification (8 index updates per INSERT)
    - Server-side cursor invalidation on COMMIT (uses keyset pagination instead)

    The migration is fully idempotent — safe to restart after a crash.
    """
    conn = op.get_bind()

    # Phase 1: Create table with PK only (IF NOT EXISTS for crash recovery)
    conn.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS chat_message (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            user_id TEXT,
            role TEXT NOT NULL,
            parent_id TEXT,
            content JSON,
            output JSON,
            model_id TEXT,
            files JSON,
            sources JSON,
            embeds JSON,
            done BOOLEAN DEFAULT TRUE,
            status_history JSON,
            error JSON,
            usage JSON,
            created_at BIGINT,
            updated_at BIGINT
        )
    """)
    )
    conn.execute(sa.text("COMMIT"))
    log.info("Phase 1 complete: chat_message table created (PK only)")

    # Phase 2: Backfill with keyset pagination and per-chunk commits
    chat_table = sa.table(
        'chat',
        sa.column('id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('chat', sa.JSON()),
    )
    chat_message_table = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('role', sa.Text()),
        sa.column('parent_id', sa.Text()),
        sa.column('content', sa.JSON()),
        sa.column('output', sa.JSON()),
        sa.column('model_id', sa.Text()),
        sa.column('files', sa.JSON()),
        sa.column('sources', sa.JSON()),
        sa.column('embeds', sa.JSON()),
        sa.column('done', sa.Boolean()),
        sa.column('status_history', sa.JSON()),
        sa.column('error', sa.JSON()),
        sa.column('usage', sa.JSON()),
        sa.column('created_at', sa.BigInteger()),
        sa.column('updated_at', sa.BigInteger()),
    )

    now = int(time.time())
    last_id = ''
    total_inserted = 0
    total_failed = 0
    total_chats = 0

    while True:
        conn.execute(sa.text("BEGIN"))

        # Keyset pagination: fetch next page of chats ordered by PK
        rows = conn.execute(
            sa.select(chat_table.c.id, chat_table.c.user_id, chat_table.c.chat)
            .where(chat_table.c.id > last_id)
            .where(~chat_table.c.user_id.like('shared-%'))
            .order_by(chat_table.c.id)
            .limit(CHAT_PAGE_SIZE)
        ).fetchall()

        if not rows:
            conn.execute(sa.text("COMMIT"))
            break

        last_id = rows[-1][0]
        total_chats += len(rows)

        # Parse all messages from this page of chats
        messages_batch = []
        for chat_row in rows:
            messages_batch.extend(
                _parse_chat_messages(chat_row[0], chat_row[1], chat_row[2], now)
            )

        # Insert in sub-batches with ON CONFLICT DO NOTHING
        for i in range(0, len(messages_batch), BATCH_SIZE):
            batch = messages_batch[i : i + BATCH_SIZE]
            inserted, failed = _flush_batch_pg(conn, chat_message_table, batch)
            total_inserted += inserted
            total_failed += failed

        conn.execute(sa.text("COMMIT"))

        if total_inserted % 50000 < max(len(messages_batch), 1):
            log.info(
                f'Migration progress: {total_chats} chats processed,'
                f' {total_inserted} messages inserted...'
            )

    log.info(
        f'Phase 2 complete: backfilled {total_inserted} messages'
        f' from {total_chats} chats ({total_failed} failed)'
    )

    # Phase 3: Create indexes (bulk construction is orders of magnitude faster
    # than per-row maintenance during the backfill)
    log.info("Phase 3: creating indexes...")
    conn.execute(sa.text("BEGIN"))
    for stmt in [
        "CREATE INDEX IF NOT EXISTS ix_chat_message_chat_id ON chat_message (chat_id)",
        "CREATE INDEX IF NOT EXISTS ix_chat_message_user_id ON chat_message (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_chat_message_model_id ON chat_message (model_id)",
        "CREATE INDEX IF NOT EXISTS ix_chat_message_created_at ON chat_message (created_at)",
        "CREATE INDEX IF NOT EXISTS chat_message_chat_parent_idx ON chat_message (chat_id, parent_id)",
        "CREATE INDEX IF NOT EXISTS chat_message_model_created_idx ON chat_message (model_id, created_at)",
        "CREATE INDEX IF NOT EXISTS chat_message_user_created_idx ON chat_message (user_id, created_at)",
    ]:
        conn.execute(sa.text(stmt))
    conn.execute(sa.text("COMMIT"))
    log.info("Phase 3 complete: indexes created")

    # Phase 4: Add FK constraint
    # NOT VALID skips validation of existing rows during creation
    log.info("Phase 4: adding foreign key constraint...")
    conn.execute(sa.text("BEGIN"))
    fk_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = 'chat_message_chat_id_fkey' "
            "AND table_name = 'chat_message'"
        )
    ).fetchone()

    if not fk_exists:
        conn.execute(
            sa.text(
                "ALTER TABLE chat_message ADD CONSTRAINT chat_message_chat_id_fkey "
                "FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE CASCADE NOT VALID"
            )
        )
    conn.execute(sa.text("COMMIT"))

    # VALIDATE CONSTRAINT checks existing rows without ACCESS EXCLUSIVE lock
    conn.execute(sa.text("BEGIN"))
    conn.execute(
        sa.text(
            "ALTER TABLE chat_message VALIDATE CONSTRAINT chat_message_chat_id_fkey"
        )
    )
    log.info("Phase 4 complete: foreign key constraint added and validated")
    # Leave transaction open for Alembic to commit (updates alembic_version)


def downgrade() -> None:
    op.drop_index('chat_message_user_created_idx', table_name='chat_message')
    op.drop_index('chat_message_model_created_idx', table_name='chat_message')
    op.drop_index('chat_message_chat_parent_idx', table_name='chat_message')
    op.drop_table('chat_message')
