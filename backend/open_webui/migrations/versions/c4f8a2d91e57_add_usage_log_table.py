"""Add usage_log table

Revision ID: c4f8a2d91e57
Revises: 42e2978c7933
Create Date: 2026-07-13 00:00:00.000000

"""

import json
import logging
import time
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

log = logging.getLogger(__name__)

revision: str = 'c4f8a2d91e57'
down_revision: Union[str, None] = '42e2978c7933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BATCH_SIZE = 5000


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _extract_tokens(usage: dict) -> tuple[int, int, int, int, int]:
    """(input, output, cached, reasoning, total) from a raw usage dict.

    Legacy chat_message rows may hold un-normalized provider payloads, so
    fall back through OpenAI / Ollama / llama.cpp key names.
    """
    input_tokens = _int(
        usage.get('input_tokens')
        or usage.get('prompt_tokens')
        or usage.get('prompt_eval_count')
        or usage.get('prompt_n')
    )
    output_tokens = _int(
        usage.get('output_tokens')
        or usage.get('completion_tokens')
        or usage.get('eval_count')
        or usage.get('predicted_n')
    )
    cached_tokens = _int(
        (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        or usage.get('cache_read_input_tokens')
        or (usage.get('input_tokens_details') or {}).get('cached_tokens')
    )
    reasoning_tokens = _int(
        (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
        or (usage.get('output_tokens_details') or {}).get('reasoning_tokens')
    )
    total_tokens = _int(usage.get('total_tokens')) or (input_tokens + output_tokens)
    return input_tokens, output_tokens, cached_tokens, reasoning_tokens, total_tokens


def _flush_batch(conn, table, batch):
    """Insert a batch, falling back to row-by-row on error (savepoints)."""
    savepoint = conn.begin_nested()
    try:
        conn.execute(sa.insert(table), batch)
        savepoint.commit()
        return len(batch), 0
    except Exception:
        savepoint.rollback()
        inserted = 0
        failed = 0
        for row in batch:
            sp = conn.begin_nested()
            try:
                conn.execute(sa.insert(table).values(**row))
                sp.commit()
                inserted += 1
            except Exception as e:
                sp.rollback()
                failed += 1
                log.warning(f'Failed to insert usage log {row["id"]}: {e}')
        return inserted, failed


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'usage_log' in existing_tables:
        return  # Already created — skip everything

    # Step 1: Create table. Deliberately no foreign keys: rows must survive
    # chat and user deletion (immutable billing ledger).
    op.create_table(
        'usage_log',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=False, index=True),
        sa.Column('chat_id', sa.Text(), nullable=True),
        sa.Column('message_id', sa.Text(), nullable=True, index=True),
        sa.Column('session_id', sa.Text(), nullable=True),
        sa.Column('model_id', sa.Text(), nullable=False, index=True),
        sa.Column('source', sa.Text(), nullable=False, server_default='chat'),
        sa.Column('task', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='completed'),
        sa.Column('input_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('cached_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('reasoning_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('usage', sa.JSON(), nullable=True),
        sa.Column('pricing', sa.JSON(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False, index=True),
    )

    op.create_index('usage_log_user_created_idx', 'usage_log', ['user_id', 'created_at'])
    op.create_index('usage_log_model_created_idx', 'usage_log', ['model_id', 'created_at'])

    if 'chat_message' not in existing_tables:
        return

    # Step 2: Backfill from existing chat_message assistant rows so history
    # doesn't reset. No pricing snapshot exists for these — cost stays NULL
    # and analytics fall back to current pricing at query time.
    chat_message_table = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('role', sa.Text()),
        sa.column('model_id', sa.Text()),
        sa.column('usage', sa.JSON()),
        sa.column('created_at', sa.BigInteger()),
    )

    usage_log_table = sa.table(
        'usage_log',
        sa.column('id', sa.Text()),
        sa.column('user_id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('message_id', sa.Text()),
        sa.column('session_id', sa.Text()),
        sa.column('model_id', sa.Text()),
        sa.column('source', sa.Text()),
        sa.column('task', sa.Text()),
        sa.column('status', sa.Text()),
        sa.column('input_tokens', sa.BigInteger()),
        sa.column('output_tokens', sa.BigInteger()),
        sa.column('cached_tokens', sa.BigInteger()),
        sa.column('reasoning_tokens', sa.BigInteger()),
        sa.column('total_tokens', sa.BigInteger()),
        sa.column('usage', sa.JSON()),
        sa.column('pricing', sa.JSON()),
        sa.column('cost', sa.Float()),
        sa.column('currency', sa.Text()),
        sa.column('created_at', sa.BigInteger()),
    )

    result = conn.execute(
        sa.select(
            chat_message_table.c.id,
            chat_message_table.c.chat_id,
            chat_message_table.c.user_id,
            chat_message_table.c.model_id,
            chat_message_table.c.usage,
            chat_message_table.c.created_at,
        )
        .where(chat_message_table.c.role == 'assistant')
        .where(chat_message_table.c.usage.isnot(None))
        .where(chat_message_table.c.user_id.isnot(None))
        .where(chat_message_table.c.model_id.isnot(None))
        .execution_options(yield_per=1000, stream_results=True)
    )

    now = int(time.time())
    batch = []
    total_inserted = 0
    total_failed = 0

    for row in result:
        composite_id, chat_id, user_id, model_id, usage, created_at = row

        if isinstance(usage, str):
            try:
                usage = json.loads(usage)
            except Exception:
                continue
        if not isinstance(usage, dict) or not usage:
            continue

        input_tokens, output_tokens, cached_tokens, reasoning_tokens, total_tokens = _extract_tokens(usage)

        prefix = f'{chat_id}-'
        message_id = composite_id[len(prefix) :] if composite_id.startswith(prefix) else composite_id

        timestamp = created_at or now
        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000
        if timestamp < 1577836800 or timestamp > now + 86400:
            timestamp = now

        batch.append(
            {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'chat_id': chat_id,
                'message_id': message_id,
                'session_id': None,
                'model_id': model_id,
                'source': 'chat',
                'task': None,
                'status': 'completed',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cached_tokens': cached_tokens,
                'reasoning_tokens': reasoning_tokens,
                'total_tokens': total_tokens,
                'usage': usage,
                'pricing': None,
                'cost': None,
                'currency': None,
                'created_at': timestamp,
            }
        )

        if len(batch) >= BATCH_SIZE:
            inserted, failed = _flush_batch(conn, usage_log_table, batch)
            total_inserted += inserted
            total_failed += failed
            if total_inserted % 50000 < BATCH_SIZE:
                log.info(f'Migration progress: {total_inserted} usage log rows inserted...')
            batch.clear()

    if batch:
        inserted, failed = _flush_batch(conn, usage_log_table, batch)
        total_inserted += inserted
        total_failed += failed

    log.info(f'Backfilled {total_inserted} rows into usage_log table ({total_failed} failed)')


def downgrade() -> None:
    op.drop_index('usage_log_model_created_idx', table_name='usage_log')
    op.drop_index('usage_log_user_created_idx', table_name='usage_log')
    op.drop_table('usage_log')
