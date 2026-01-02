"""
Add moderation_session_activity table

Revision ID: fedcba987654
Revises: ff23ac45bd67
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "fedcba987654"
down_revision = "ff23ac45bd67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "moderation_session_activity" not in existing_tables:
        # create table if not exists
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
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session_activity")]
        if "idx_mod_activity_user_child_session" not in existing_indexes:
            op.create_index(
                "idx_mod_activity_user_child_session",
                "moderation_session_activity",
                ["user_id", "child_id", "session_number"],
            )
        if "idx_mod_activity_created_at" not in existing_indexes:
            op.create_index(
                "idx_mod_activity_created_at",
                "moderation_session_activity",
                ["created_at"],
            )


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "moderation_session_activity" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session_activity")]
        if "idx_mod_activity_created_at" in existing_indexes:
            op.drop_index("idx_mod_activity_created_at", table_name="moderation_session_activity")
        if "idx_mod_activity_user_child_session" in existing_indexes:
            op.drop_index("idx_mod_activity_user_child_session", table_name="moderation_session_activity")
        op.drop_table("moderation_session_activity")
