"""Add supabase_id column to auth table

Revision ID: add_supabase_id_001
Revises: c29facfe716b
Create Date: 2025-03-07 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_supabase_id_001"
down_revision: Union[str, None] = "c29facfe716b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Add supabase_id column to auth table
    with op.batch_alter_table("auth", schema=None) as batch_op:
        batch_op.add_column(sa.Column("supabase_id", sa.String(), nullable=True))

def downgrade():
    # Remove supabase_id column from auth table
    with op.batch_alter_table("auth", schema=None) as batch_op:
        batch_op.drop_column("supabase_id") 