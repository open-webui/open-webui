"""
Add assignment_session_activity table

Revision ID: g12h34i56j78
Revises: ff23ac45bd67
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "g12h34i56j78"
down_revision = "ff23ac45bd67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "assignment_session_activity" not in existing_tables:
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
    else:
        # Table exists, check what columns it has and create indexes accordingly
        existing_columns = [col["name"] for col in inspector.get_columns("assignment_session_activity")]
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("assignment_session_activity")]
        
        # Only create indexes for columns that exist
        if "idx_assignment_activity_created_at" not in existing_indexes and "created_at" in existing_columns:
            op.create_index(
                "idx_assignment_activity_created_at",
                "assignment_session_activity",
                ["created_at"],
            )
        
        # Only create composite index if all columns exist
        if "idx_assignment_activity_user_child_attempt" not in existing_indexes:
            if all(col in existing_columns for col in ["user_id", "child_id", "attempt_number"]):
                op.create_index(
                    "idx_assignment_activity_user_child_attempt",
                    "assignment_session_activity",
                    ["user_id", "child_id", "attempt_number"],
                )
            elif all(col in existing_columns for col in ["user_id", "attempt_number"]):
                # Fallback: create index without child_id if it doesn't exist
                op.create_index(
                    "idx_assignment_activity_user_attempt",
                    "assignment_session_activity",
                    ["user_id", "attempt_number"],
                )


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "assignment_session_activity" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("assignment_session_activity")]
        if "idx_assignment_activity_created_at" in existing_indexes:
            op.drop_index("idx_assignment_activity_created_at", table_name="assignment_session_activity")
        if "idx_assignment_activity_user_child_attempt" in existing_indexes:
            op.drop_index("idx_assignment_activity_user_child_attempt", table_name="assignment_session_activity")
        if "idx_assignment_activity_user_attempt" in existing_indexes:
            op.drop_index("idx_assignment_activity_user_attempt", table_name="assignment_session_activity")
        op.drop_table("assignment_session_activity")
