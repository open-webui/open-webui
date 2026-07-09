"""Add memory (id, user_id) covering index

Revision ID: 55f1302ac17c
Revises: 42e2978c7933
Create Date: 2026-07-09 20:54:25.379896

"""

import sqlalchemy as sa
from alembic import op

revision = '55f1302ac17c'
down_revision = '42e2978c7933'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('memory')}

    if 'ix_memory_id_user_id' not in existing_indexes:
        op.create_index('ix_memory_id_user_id', 'memory', ['id', 'user_id'])


def downgrade():
    op.drop_index('ix_memory_id_user_id', table_name='memory')
