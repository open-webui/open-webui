"""Add child_marker column to selection table

Revision ID: d1e2f3a4b5c6
Revises: b1c2d3e4f5a6
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add child_marker column to selection table
    op.add_column('selection', sa.Column('child_marker', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove child_marker column from selection table
    op.drop_column('selection', 'child_marker')
