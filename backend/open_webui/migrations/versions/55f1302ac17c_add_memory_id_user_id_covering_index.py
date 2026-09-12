"""Add memory (id, user_id) covering index

Revision ID: 55f1302ac17c
Revises: b0018471bbbe
Create Date: 2026-07-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '55f1302ac17c'
down_revision: Union[str, None] = 'b0018471bbbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = {index['name'] for index in inspector.get_indexes('memory')}

    if 'ix_memory_id_user_id' not in indexes:
        op.create_index('ix_memory_id_user_id', 'memory', ['id', 'user_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = {index['name'] for index in inspector.get_indexes('memory')}

    if 'ix_memory_id_user_id' in indexes:
        op.drop_index('ix_memory_id_user_id', table_name='memory')
