"""Add updated_at to model_system_prompt_binding

Revision ID: a9b8c7d6e5f4
Revises: f8e7d6c5b4a3
Create Date: 2026-07-17 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'f8e7d6c5b4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())
    if 'model_system_prompt_binding' not in existing_tables:
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    bind_cols = {col['name'] for col in inspector.get_columns('model_system_prompt_binding')}
    if 'updated_at' not in bind_cols:
        op.add_column(
            'model_system_prompt_binding',
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )


def downgrade() -> None:
    existing_tables = set(get_existing_tables())
    if 'model_system_prompt_binding' not in existing_tables:
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    bind_cols = {col['name'] for col in inspector.get_columns('model_system_prompt_binding')}
    if 'updated_at' in bind_cols:
        op.drop_column('model_system_prompt_binding', 'updated_at')
