"""Update folder table data

Revision ID: d31026856c01
Revises: 9f0c9cd09105
Create Date: 2025-07-13 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "d31026856c01"
down_revision = "9f0c9cd09105"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("folder", sa.Column("data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("folder", "data")
