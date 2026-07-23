"""add snapshot column to model_system_prompt_history

Revision ID: b3c4d5e6f7a0
Revises: af2b3c4d5e6f
Create Date: 2026-07-13 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a0'
down_revision: Union[str, None] = 'af2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c['name'] for c in inspector.get_columns('model_system_prompt_history')}
    if 'snapshot' not in existing_columns:
        op.add_column('model_system_prompt_history', sa.Column('snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c['name'] for c in inspector.get_columns('model_system_prompt_history')}
    if 'snapshot' in existing_columns:
        op.drop_column('model_system_prompt_history', 'snapshot')