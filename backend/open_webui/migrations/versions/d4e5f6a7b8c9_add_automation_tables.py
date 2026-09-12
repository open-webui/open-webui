"""add automation tables

Revision ID: d4e5f6a7b8c9
Revises: f1e2d3c4b5a6
Create Date: 2026-03-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'a3dd5bedd151'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    """Check if an index already exists on the given table (works for both SQLite and PostgreSQL)."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'automation' not in tables:
        op.create_table(
            'automation',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('data', sa.JSON(), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('last_run_at', sa.BigInteger(), nullable=True),
            sa.Column('next_run_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    inspector.clear_cache()
    if 'automation' in inspector.get_table_names():
        if not _index_exists(inspector, 'ix_automation_next_run', 'automation'):
            op.create_index('ix_automation_next_run', 'automation', ['next_run_at'])

    if 'automation_run' not in tables:
        op.create_table(
            'automation_run',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('automation_id', sa.Text(), nullable=False),
            sa.Column('chat_id', sa.Text(), nullable=True),
            sa.Column('status', sa.Text(), nullable=False),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    inspector.clear_cache()
    if 'automation_run' in inspector.get_table_names():
        if not _index_exists(inspector, 'ix_automation_run_automation_id', 'automation_run'):
            op.create_index(
                'ix_automation_run_automation_id',
                'automation_run',
                ['automation_id'],
            )


def downgrade():
    op.drop_index('ix_automation_run_automation_id')
    op.drop_table('automation_run')
    op.drop_index('ix_automation_next_run')
    op.drop_table('automation')
