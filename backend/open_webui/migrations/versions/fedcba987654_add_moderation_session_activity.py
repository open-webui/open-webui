"""
Add moderation_session_activity table

Revision ID: fedcba987654
Revises: ff23ac45bd67
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa

revision = "fedcba987654"
down_revision = "ff23ac45bd67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("moderation_session_activity", schema=None) as batch_op:
        pass
    # create table if not exists (batch_alter_table can't create; use op.create_table)
    op.create_table(
        "moderation_session_activity",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("child_id", sa.Text(), nullable=False),
        sa.Column("session_number", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("active_ms_delta", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cumulative_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_mod_activity_user_child_session",
        "moderation_session_activity",
        ["user_id", "child_id", "session_number"],
    )
    op.create_index(
        "idx_mod_activity_created_at",
        "moderation_session_activity",
        ["created_at"],
    )
    # Drop server defaults post creation
    with op.batch_alter_table("moderation_session_activity") as batch_op:
        batch_op.alter_column("session_number", server_default=None)
        batch_op.alter_column("active_ms_delta", server_default=None)
        batch_op.alter_column("cumulative_ms", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_mod_activity_created_at", table_name="moderation_session_activity")
    op.drop_index("idx_mod_activity_user_child_session", table_name="moderation_session_activity")
    op.drop_table("moderation_session_activity")


