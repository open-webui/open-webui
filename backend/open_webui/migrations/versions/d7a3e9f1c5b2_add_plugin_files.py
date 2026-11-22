"""Add supporting files to tools and functions.

Revision ID: d7a3e9f1c5b2
Revises: c4e1a7d93b20
"""

import sqlalchemy as sa
from alembic import op
from open_webui.internal.db import JSONField

revision = 'd7a3e9f1c5b2'
down_revision = 'c4e1a7d93b20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tool', sa.Column('files', JSONField(), nullable=True))
    op.add_column('function', sa.Column('files', JSONField(), nullable=True))


def downgrade():
    op.drop_column('function', 'files')
    op.drop_column('tool', 'files')
