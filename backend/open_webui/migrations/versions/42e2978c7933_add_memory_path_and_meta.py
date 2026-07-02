"""add memory path and meta

Revision ID: 42e2978c7933
Revises: 7b3f2a9c1d4e
Create Date: 2026-06-29 05:35:50.565887

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '42e2978c7933'
down_revision: Union[str, None] = '7b3f2a9c1d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('memory')}

    if 'path' not in columns:
        op.add_column('memory', sa.Column('path', sa.Text(), nullable=True))
    if 'meta' not in columns:
        op.add_column('memory', sa.Column('meta', sa.JSON(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('memory')}

    if 'meta' in columns:
        op.drop_column('memory', 'meta')
    if 'path' in columns:
        op.drop_column('memory', 'path')
