"""Add usage_ledger table and change chat_message.chat_id FK to SET NULL

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-04-08 10:00:00.000000

- Adds usage_ledger table for tracking temp chat and direct API call usage
- Changes chat_message.chat_id from CASCADE to SET NULL and makes it nullable,
  so usage metadata survives when chats are deleted
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Create usage_ledger table
    if 'usage_ledger' not in existing_tables:
        op.create_table(
            'usage_ledger',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('model_id', sa.Text(), nullable=True),
            sa.Column('input_tokens', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('output_tokens', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('ix_usage_ledger_user_id', 'usage_ledger', ['user_id'])
        op.create_index('ix_usage_ledger_created_at', 'usage_ledger', ['created_at'])
        op.create_index('usage_ledger_user_created_idx', 'usage_ledger', ['user_id', 'created_at'])

    # Change chat_message.chat_id: CASCADE -> SET NULL, make nullable
    if 'chat_message' in existing_tables:
        if dialect == 'postgresql':
            conn.execute(sa.text(
                'ALTER TABLE chat_message ALTER COLUMN chat_id DROP NOT NULL'
            ))
            conn.execute(sa.text(
                'ALTER TABLE chat_message DROP CONSTRAINT IF EXISTS chat_message_chat_id_fkey'
            ))
            conn.execute(sa.text(
                'ALTER TABLE chat_message ADD CONSTRAINT chat_message_chat_id_fkey '
                'FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE SET NULL'
            ))
        else:
            # SQLite: use batch mode (recreates table)
            with op.batch_alter_table('chat_message') as batch:
                batch.alter_column('chat_id', existing_type=sa.Text(), nullable=True)
                batch.drop_constraint('chat_message_chat_id_fkey', type_='foreignkey')
                batch.create_foreign_key(
                    'chat_message_chat_id_fkey',
                    'chat',
                    ['chat_id'],
                    ['id'],
                    ondelete='SET NULL',
                )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        conn.execute(sa.text(
            'ALTER TABLE chat_message DROP CONSTRAINT IF EXISTS chat_message_chat_id_fkey'
        ))
        conn.execute(sa.text(
            'ALTER TABLE chat_message ADD CONSTRAINT chat_message_chat_id_fkey '
            'FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE CASCADE'
        ))
        conn.execute(sa.text(
            'ALTER TABLE chat_message ALTER COLUMN chat_id SET NOT NULL'
        ))
    else:
        with op.batch_alter_table('chat_message') as batch:
            batch.drop_constraint('chat_message_chat_id_fkey', type_='foreignkey')
            batch.create_foreign_key(
                'chat_message_chat_id_fkey',
                'chat',
                ['chat_id'],
                ['id'],
                ondelete='CASCADE',
            )
            batch.alter_column('chat_id', existing_type=sa.Text(), nullable=False)

    op.drop_index('usage_ledger_user_created_idx', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_created_at', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_user_id', table_name='usage_ledger')
    op.drop_table('usage_ledger')
