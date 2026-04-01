"""add automation tables

Revision ID: d4e5f6a7b8c9
Revises: f1e2d3c4b5a6
Create Date: 2026-03-30
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'a3dd5bedd151'
branch_labels = None
depends_on = None


def upgrade():
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
    op.create_index('ix_automation_next_run', 'automation', ['next_run_at'])

    op.create_table(
        'automation_run',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('automation_id', sa.Text(), nullable=False),
        sa.Column('chat_id', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
    )
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
