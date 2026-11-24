"""Add private per-user folder working views."""

import sqlalchemy as sa
from alembic import op

revision = 'd2f86c0b41ae'
down_revision = 'b7d4f1a2c960'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'folder_view_state',
        sa.Column('user_id', sa.Text(), primary_key=True),
        sa.Column('folder_id', sa.Text(), primary_key=True),
        sa.Column('state', sa.JSON(), nullable=False),
        sa.Column('revision', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('ix_folder_view_state_folder_id', 'folder_view_state', ['folder_id'])


def downgrade():
    op.drop_table('folder_view_state')
