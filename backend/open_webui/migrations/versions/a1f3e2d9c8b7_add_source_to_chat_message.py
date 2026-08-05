"""add source column to chat_message, make chat_id nullable

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
    indexes = {i['name'] for i in inspector.get_indexes('chat_message')}

    # Add source column if not present.
    # op.add_column does not create indexes; we must call op.create_index separately.
    if 'source' not in columns:
        op.add_column('chat_message', sa.Column('source', sa.Text(), nullable=True))
        if 'ix_chat_message_source' not in indexes:
            op.create_index('ix_chat_message_source', 'chat_message', ['source'])

    # Make chat_id nullable.  The FK constraint is intentionally kept: NULL values
    # are exempt from FK checks, so API rows (chat_id=NULL) pass through; regular
    # chat rows retain ON DELETE CASCADE referential integrity.
    if dialect == 'sqlite':
        with op.batch_alter_table('chat_message', recreate='always') as batch_op:
            batch_op.alter_column('chat_id', existing_type=sa.Text(), nullable=True)
    else:
        op.alter_column('chat_message', 'chat_id', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    dialect = conn.dialect.name
    columns = {c['name'] for c in inspector.get_columns('chat_message')}
    indexes = {i['name'] for i in inspector.get_indexes('chat_message')}

    if 'source' in columns:
        if 'ix_chat_message_source' in indexes:
            op.drop_index('ix_chat_message_source', 'chat_message')
        op.drop_column('chat_message', 'source')

    # Restore chat_id to NOT NULL (data must already be clean — no NULLs)
    if dialect == 'sqlite':
        with op.batch_alter_table('chat_message', recreate='always') as batch_op:
            batch_op.alter_column('chat_id', existing_type=sa.Text(), nullable=False)
    else:
        op.alter_column('chat_message', 'chat_id', existing_type=sa.Text(), nullable=False)
