"""Add private per-user chat working views."""

import sqlalchemy as sa
from alembic import op

revision = '6a23bd107e54'
down_revision = '8bc7e5a902d1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chat_view_state',
        sa.Column('user_id', sa.Text(), primary_key=True),
        sa.Column('chat_id', sa.Text(), primary_key=True),
        sa.Column('state', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('ix_chat_view_state_chat_id', 'chat_view_state', ['chat_id'])


def downgrade():
    op.drop_table('chat_view_state')
