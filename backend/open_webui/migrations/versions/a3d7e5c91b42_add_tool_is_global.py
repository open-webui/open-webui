"""Add a global flag to tools.

Revision ID: a3d7e5c91b42
Revises: e42c8f710a36
"""

import sqlalchemy as sa
from alembic import op

revision = 'a3d7e5c91b42'
down_revision = 'e42c8f710a36'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tool', sa.Column('is_global', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('tool', 'is_global')
