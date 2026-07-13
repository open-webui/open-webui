"""Add base_model_id to usage_log

Revision ID: e91b3d47a2c6
Revises: c4f8a2d91e57
Create Date: 2026-07-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e91b3d47a2c6'
down_revision: Union[str, None] = 'c4f8a2d91e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'usage_log' not in inspector.get_table_names():
        return

    columns = {col['name'] for col in inspector.get_columns('usage_log')}
    if 'base_model_id' not in columns:
        # The underlying model that actually served a workspace/preset model,
        # captured at generation time so later base-model changes stay visible
        # in history. NULL for direct models and pre-existing rows.
        op.add_column('usage_log', sa.Column('base_model_id', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'usage_log' not in inspector.get_table_names():
        return

    columns = {col['name'] for col in inspector.get_columns('usage_log')}
    if 'base_model_id' in columns:
        op.drop_column('usage_log', 'base_model_id')
