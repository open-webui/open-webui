"""add source column to chat_message, make chat_id nullable, drop FK

Revision ID: a1f3e2d9c8b7
Revises: f0bd01a18a3d
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a1f3e2d9c8b7'
down_revision: Union[str, None] = 'f0bd01a18a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    dialect = conn.dialect.name
    columns = {c['name'] for c in inspector.get_columns('chat_message')}

    # Add source column if not present
    if 'source' not in columns:
        op.add_column('chat_message', sa.Column('source', sa.Text(), nullable=True, index=True))

    # Make chat_id nullable and drop FK constraint.
    # SQLite does not support DROP CONSTRAINT; we use batch_alter_table which
    # rewrites the table transparently on SQLite and uses ALTER on PostgreSQL.
    if dialect == 'sqlite':
        with op.batch_alter_table('chat_message', recreate='always') as batch_op:
            batch_op.alter_column('chat_id', existing_type=sa.Text(), nullable=True)
            # Drop FK by not including it in the recreated table definition.
            # batch_alter_table with recreate='always' drops all existing FKs
            # unless explicitly re-added; since we omit the FK here it is gone.
    else:
        # PostgreSQL: drop the FK constraint by name, then alter column
        fks = inspector.get_foreign_keys('chat_message')
        for fk in fks:
            if 'chat_id' in fk.get('constrained_columns', []):
                op.drop_constraint(fk['name'], 'chat_message', type_='foreignkey')
        op.alter_column('chat_message', 'chat_id', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    dialect = conn.dialect.name
    columns = {c['name'] for c in inspector.get_columns('chat_message')}

    if 'source' in columns:
        op.drop_column('chat_message', 'source')

    # Restore chat_id to NOT NULL (data must already be clean — no NULLs)
    if dialect == 'sqlite':
        with op.batch_alter_table('chat_message', recreate='always') as batch_op:
            batch_op.alter_column('chat_id', existing_type=sa.Text(), nullable=False)
            batch_op.create_foreign_key(
                'fk_chat_message_chat_id',
                'chat',
                ['chat_id'],
                ['id'],
                ondelete='CASCADE',
            )
    else:
        op.alter_column('chat_message', 'chat_id', existing_type=sa.Text(), nullable=False)
        op.create_foreign_key(
            'fk_chat_message_chat_id',
            'chat_message',
            'chat',
            ['chat_id'],
            ['id'],
            ondelete='CASCADE',
        )
