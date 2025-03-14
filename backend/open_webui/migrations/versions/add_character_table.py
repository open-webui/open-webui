"""Add character table

Revision ID: 9c2d3713
Revises: 3781e22d8b01
Create Date: 2024-10-01 14:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
import json
from open_webui.migrations.util import get_existing_tables



revision = "9c2d3713"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade():
    # Creating the 'knowledge' table
    existing_tables = set(get_existing_tables())
    
    if "character" not in existing_tables:
        print("Creating character table")
        
        op.create_table(
            "character",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.UniqueConstraint("id"),
        )

def downgrade():
    op.drop_table("knowledge")
