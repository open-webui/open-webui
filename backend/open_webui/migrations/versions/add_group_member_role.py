"""add_group_member_role

Revision ID: 4e5f6a7b8c9d
Revises: 37f288994c47
Create Date: 2025-11-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e5f6a7b8c9d"
down_revision: Union[str, None] = "37f288994c47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to group_member table with default value 'member'
    op.add_column(
        "group_member",
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
    )


def downgrade() -> None:
    op.drop_column("group_member", "role")
