"""Add role and role_capability tables for RBAC

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-19 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return table_name in insp.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _table_exists("role"):
        op.create_table(
            "role",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("permissions", sa.JSON(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("role_name_idx", "role", ["name"])
        op.create_index("role_priority_idx", "role", ["priority"])

    if not _table_exists("role_capability"):
        op.create_table(
            "role_capability",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "role_id",
                sa.Text(),
                sa.ForeignKey("role.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("capability", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("role_capability_role_id_idx", "role_capability", ["role_id"])
        op.create_index(
            "role_capability_capability_idx", "role_capability", ["capability"]
        )
        op.create_index(
            "role_capability_unique_idx",
            "role_capability",
            ["role_id", "capability"],
            unique=True,
        )

    if not _column_exists("user", "role_id"):
        op.add_column(
            "user",
            sa.Column("role_id", sa.Text(), nullable=True),
        )
        op.create_index("user_role_id_idx", "user", ["role_id"])


def downgrade() -> None:
    op.drop_index("user_role_id_idx", table_name="user")
    op.drop_column("user", "role_id")

    op.drop_index("role_capability_unique_idx", table_name="role_capability")
    op.drop_index("role_capability_capability_idx", table_name="role_capability")
    op.drop_index("role_capability_role_id_idx", table_name="role_capability")
    op.drop_table("role_capability")

    op.drop_index("role_priority_idx", table_name="role")
    op.drop_index("role_name_idx", table_name="role")
    op.drop_table("role")
