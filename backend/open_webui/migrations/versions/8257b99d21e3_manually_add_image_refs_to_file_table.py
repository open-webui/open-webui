"""Manually add image_refs to file table

Revision ID: 8257b99d21e3
Revises: 3af16a1c9fb6
Create Date: 2025-08-28 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '<REPLACE_WITH_NEW_ID>' # <-- IMPORTANT: Copy the new ID here
down_revision: Union[str, None] = '3af16a1c9fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_refs', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_column('image_refs')
