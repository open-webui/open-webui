"""Add memory user_id index

Revision ID: a0b1c2d3e4f5
Revises: 4de81c2a3af1
Create Date: 2025-09-15 03:00:00.000000

"""

from alembic import op

revision = 'a0b1c2d3e4f5'
down_revision = '4de81c2a3af1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_memory_user_id', 'memory', ['user_id'])


def downgrade():
    op.drop_index('ix_memory_user_id', table_name='memory')
