"""Add Charity table

Revision ID: 5ca4b28d4bc8
Revises: d31026856c01
Create Date: 2025-07-17 16:12:40.926393

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "5ca4b28d4bc8"
down_revision: Union[str, None] = "d31026856c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "charity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("charity_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("is_imported", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("charity_id"),
    )
    op.create_index("ix_charity_name", "charity", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_charity_name", table_name="charity")
    op.drop_table("charity")
