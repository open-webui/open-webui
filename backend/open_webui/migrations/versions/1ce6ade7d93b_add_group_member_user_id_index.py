"""Add group_member user_id index

Revision ID: 1ce6ade7d93b
Revises: f0bd01a18a3d
Create Date: 2026-07-31 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = '1ce6ade7d93b'
down_revision = 'f0bd01a18a3d'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('group_member')}

    if 'ix_group_member_user_id_group_id' not in existing_indexes:
        op.create_index('ix_group_member_user_id_group_id', 'group_member', ['user_id', 'group_id'])


def downgrade():
    op.drop_index('ix_group_member_user_id_group_id', table_name='group_member')
