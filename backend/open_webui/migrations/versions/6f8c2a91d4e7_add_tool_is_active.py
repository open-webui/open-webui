"""Add a persistent enabled state to tools.

Revision ID: 6f8c2a91d4e7
Revises: c41f8d9e2a10
"""

import sqlalchemy as sa
from alembic import op

revision = '6f8c2a91d4e7'
down_revision = 'c41f8d9e2a10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tool', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column('tool', 'is_active')
