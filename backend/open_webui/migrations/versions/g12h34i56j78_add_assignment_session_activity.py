"""
Add assignment_session_activity table

Revision ID: g12h34i56j78
Revises: ff23ac45bd67
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa

revision = "g12h34i56j78"
down_revision = "ff23ac45bd67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create table
    op.create_table(
        "assignment_session_activity",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("child_id", sa.Text(), nullable=True),  # Nullable since child may not exist initially
        sa.Column("attempt_number", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("active_ms_delta", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cumulative_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_assignment_activity_user_child_attempt",
        "assignment_session_activity",
        ["user_id", "child_id", "attempt_number"],
    )
    op.create_index(
        "idx_assignment_activity_created_at",
        "assignment_session_activity",
        ["created_at"],
    )
    # Drop server defaults post creation
    with op.batch_alter_table("assignment_session_activity") as batch_op:
        batch_op.alter_column("attempt_number", server_default=None)
        batch_op.alter_column("active_ms_delta", server_default=None)
        batch_op.alter_column("cumulative_ms", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_assignment_activity_created_at", table_name="assignment_session_activity")
    op.drop_index("idx_assignment_activity_user_child_attempt", table_name="assignment_session_activity")
    op.drop_table("assignment_session_activity")







