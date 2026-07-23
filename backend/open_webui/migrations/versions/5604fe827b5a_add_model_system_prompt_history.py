"""add model_system_prompt_history table and system_prompt_version_id column

Revision ID: 5604fe827b5a
Revises: 42e2978c7933
Create Date: 2026-07-09 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5604fe827b5a'
down_revision: Union[str, None] = '42e2978c7933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'model_system_prompt_history' not in existing_tables:
        op.create_table(
            'model_system_prompt_history',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('model_id', sa.Text(), nullable=False, index=True),
            sa.Column('parent_id', sa.Text(), nullable=True),
            sa.Column('system_prompt', sa.Text(), nullable=False, server_default=''),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('commit_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    if 'model' in existing_tables:
        model_cols = {c['name'] for c in inspector.get_columns('model')}
        if 'system_prompt_version_id' not in model_cols:
            op.add_column('model', sa.Column('system_prompt_version_id', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'model_system_prompt_history' in existing_tables:
        op.drop_table('model_system_prompt_history')

    if 'model' in existing_tables:
        model_cols = {c['name'] for c in inspector.get_columns('model')}
        if 'system_prompt_version_id' in model_cols:
            op.drop_column('model', 'system_prompt_version_id')