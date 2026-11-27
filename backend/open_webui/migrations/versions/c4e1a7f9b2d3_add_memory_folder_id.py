"""Add folder_id to memory."""

import sqlalchemy as sa
from alembic import op

revision = 'c4e1a7f9b2d3'
down_revision = '5e7a2c9d4b13'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('memory', sa.Column('folder_id', sa.Text(), nullable=True))
    op.create_index('ix_memory_user_id_folder_id', 'memory', ['user_id', 'folder_id'])


def downgrade():
    op.drop_index('ix_memory_user_id_folder_id', table_name='memory')
    op.drop_column('memory', 'folder_id')
