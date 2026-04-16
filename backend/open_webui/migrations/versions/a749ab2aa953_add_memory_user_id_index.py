"""Add index on memory.user_id

Revision ID: a749ab2aa953
Revises: e1f2a3b4c5d6
Create Date: 2026-04-16 00:00:00.000000

"""

from alembic import op

revision = 'a749ab2aa953'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    # Memory.user_id is filtered on every per-user query
    # (get_memories_by_user_id, delete_memories_by_user_id),
    # so a btree index prevents full-table scans as the table grows.
    op.create_index('memory_user_id_idx', 'memory', ['user_id'])


def downgrade():
    op.drop_index('memory_user_id_idx', table_name='memory')
