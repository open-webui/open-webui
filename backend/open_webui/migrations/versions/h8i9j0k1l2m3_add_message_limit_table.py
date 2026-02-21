"""Add message_limit table for daily message caps

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-02-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).fetchone()
    return result is not None


def upgrade() -> None:
    if not _table_exists("message_limit"):
        op.create_table(
            "message_limit",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("scope_type", sa.Text(), nullable=False),
            sa.Column(
                "role_id",
                sa.Text(),
                sa.ForeignKey("role.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "user_id",
                sa.Text(),
                sa.ForeignKey("user.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "max_messages_per_day", sa.BigInteger(), default=-1, nullable=False
            ),
            sa.Column("created_by", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.UniqueConstraint(
                "scope_type", "role_id", "user_id", name="uq_message_limit_scope"
            ),
        )
        op.create_index("message_limit_scope_type_idx", "message_limit", ["scope_type"])
        op.create_index("message_limit_role_id_idx", "message_limit", ["role_id"])
        op.create_index("message_limit_user_id_idx", "message_limit", ["user_id"])


def downgrade() -> None:
    op.drop_index("message_limit_user_id_idx", table_name="message_limit")
    op.drop_index("message_limit_role_id_idx", table_name="message_limit")
    op.drop_index("message_limit_scope_type_idx", table_name="message_limit")
    op.drop_table("message_limit")
