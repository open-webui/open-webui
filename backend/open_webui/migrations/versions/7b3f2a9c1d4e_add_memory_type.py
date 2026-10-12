"""add memory type

Revision ID: 7b3f2a9c1d4e
Revises: 4c5ce3d2f27f
Create Date: 2026-06-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7b3f2a9c1d4e'
down_revision: Union[str, None] = '4c5ce3d2f27f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('memory')}
    indexes = {index['name'] for index in inspector.get_indexes('memory')}

    if 'type' not in columns:
        op.add_column('memory', sa.Column('type', sa.String(), server_default='context', nullable=False))

    if 'ix_memory_type' not in indexes:
        op.create_index('ix_memory_type', 'memory', ['type'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('memory')}
    indexes = {index['name'] for index in inspector.get_indexes('memory')}

    if 'ix_memory_type' in indexes:
        op.drop_index('ix_memory_type', table_name='memory')

    if 'type' in columns:
        op.drop_column('memory', 'type')
