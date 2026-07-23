"""add model_system_prompt_comment table

Revision ID: af2b3c4d5e6f
Revises: 5604fe827b5a
Create Date: 2026-07-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'af2b3c4d5e6f'
down_revision: Union[str, None] = '5604fe827b5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'model_system_prompt_comment' not in existing_tables:
        op.create_table(
            'model_system_prompt_comment',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('history_id', sa.Text(), nullable=False, index=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'model_system_prompt_comment' in existing_tables:
        op.drop_table('model_system_prompt_comment')