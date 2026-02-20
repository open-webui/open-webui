"""Migrate from group-based oversight to direct user-to-user assignments

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-20 00:00:00.000000

"""

import time
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create oversight_assignment table
    op.create_table(
        "oversight_assignment",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "overseer_id",
            sa.Text(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            sa.Text(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Text(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "overseer_id", "target_id", name="uq_oversight_overseer_target"
        ),
        sa.CheckConstraint("overseer_id != target_id", name="ck_oversight_no_self"),
    )
    op.create_index("idx_oversight_overseer", "oversight_assignment", ["overseer_id"])
    op.create_index("idx_oversight_target", "oversight_assignment", ["target_id"])

    # 2. Backfill from existing group data
    conn = op.get_bind()
    now = int(time.time())

    # Find all group admins
    admin_rows = conn.execute(
        sa.text(
            "SELECT gm.user_id, gm.group_id, g.name "
            "FROM group_member gm "
            'JOIN "group" g ON g.id = gm.group_id '
            "WHERE gm.role = 'admin'"
        )
    ).fetchall()

    # Get all exclusions
    exclusion_rows = conn.execute(
        sa.text("SELECT group_id, user_id FROM group_oversight_exclusion")
    ).fetchall()
    exclusions = {(r[0], r[1]) for r in exclusion_rows}

    # For each admin, get all other members of their groups and create assignments
    for admin_user_id, group_id, group_name in admin_rows:
        members = conn.execute(
            sa.text(
                "SELECT user_id FROM group_member "
                "WHERE group_id = :group_id AND user_id != :admin_id"
            ),
            {"group_id": group_id, "admin_id": admin_user_id},
        ).fetchall()

        for (member_user_id,) in members:
            # Skip excluded users
            if (group_id, member_user_id) in exclusions:
                continue

            source = f"group:{group_name}"

            # Idempotent: skip if assignment already exists
            existing = conn.execute(
                sa.text(
                    "SELECT 1 FROM oversight_assignment "
                    "WHERE overseer_id = :overseer_id AND target_id = :target_id"
                ),
                {"overseer_id": admin_user_id, "target_id": member_user_id},
            ).fetchone()

            if not existing:
                conn.execute(
                    sa.text(
                        "INSERT INTO oversight_assignment "
                        "(id, overseer_id, target_id, created_by, created_at, source) "
                        "VALUES (:id, :overseer_id, :target_id, :created_by, :created_at, :source)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "overseer_id": admin_user_id,
                        "target_id": member_user_id,
                        "created_by": admin_user_id,
                        "created_at": now,
                        "source": source,
                    },
                )

    # 3. Drop group_oversight_exclusion table (no longer needed)
    op.drop_table("group_oversight_exclusion")


def downgrade() -> None:
    # Recreate group_oversight_exclusion table
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

    # Drop oversight_assignment table
    op.drop_index("idx_oversight_target", table_name="oversight_assignment")
    op.drop_index("idx_oversight_overseer", table_name="oversight_assignment")
    op.drop_table("oversight_assignment")
