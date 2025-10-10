"""Replace child_marker with child_id in selection table

Revision ID: f2g3h4i5j6k7
Revises: e1f2g3h4i5j6
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f2g3h4i5j6k7'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename child_marker column to child_id in selection table
    op.alter_column('selection', 'child_marker', new_column_name='child_id')


def downgrade() -> None:
    # Rename child_id column back to child_marker in selection table
    op.alter_column('selection', 'child_id', new_column_name='child_marker')
