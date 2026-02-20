"""Add group member roles and oversight exclusion table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-20 00:00:00.000000

"""

import time
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add role column to group_member with safe default
    op.add_column(
        "group_member",
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
    )
    op.create_index("idx_gm_user_role", "group_member", ["user_id", "role"])
    op.create_index("idx_gm_group_user", "group_member", ["group_id", "user_id"])

    # 2. Create group_oversight_exclusion table
    op.create_table(
        "group_oversight_exclusion",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Text(),
            sa.ForeignKey("group.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_oversight_excl_group_user"),
    )

    # 3. Seed audit.read_group_chats capability for admin and user roles
    conn = op.get_bind()
    now = int(time.time())

    roles = conn.execute(
        sa.text("SELECT id, name FROM role WHERE name IN ('admin', 'user')")
    ).fetchall()

    for role_row in roles:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO role_capability (id, role_id, capability, created_at) "
                "VALUES (:id, :role_id, :capability, :created_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "role_id": role_row[0],
                "capability": "audit.read_group_chats",
                "created_at": now,
            },
        )


def downgrade() -> None:
    # Remove seeded capability
    op.get_bind().execute(
        sa.text(
            "DELETE FROM role_capability WHERE capability = 'audit.read_group_chats'"
        )
    )

    op.drop_table("group_oversight_exclusion")
    op.drop_index("idx_gm_group_user", table_name="group_member")
    op.drop_index("idx_gm_user_role", table_name="group_member")
    op.drop_column("group_member", "role")
