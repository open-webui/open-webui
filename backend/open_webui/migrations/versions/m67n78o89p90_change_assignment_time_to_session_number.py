"""Change assignment time tracking from attempt_number to session_number

Revision ID: m67n78o89p90
Revises: l67m78n89o90
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "m67n78o89p90"
down_revision = "l67m78n89o90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists and what columns/indexes it has (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "assignment_session_activity" in existing_tables:
        existing_columns = [
            col["name"] for col in inspector.get_columns("assignment_session_activity")
        ]
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("assignment_session_activity")
        ]

        # Drop old index if it exists
        if "idx_assignment_activity_user_attempt" in existing_indexes:
            op.drop_index(
                "idx_assignment_activity_user_attempt",
                table_name="assignment_session_activity",
            )

        # Rename attempt_number to session_number if attempt_number exists and session_number doesn't
        if (
            "attempt_number" in existing_columns
            and "session_number" not in existing_columns
        ):
            with op.batch_alter_table("assignment_session_activity") as batch_op:
                batch_op.alter_column(
                    "attempt_number", new_column_name="session_number"
                )

        # Create new index with session_number if it doesn't exist
        if (
            "idx_assignment_activity_user_session" not in existing_indexes
            and "session_number" in existing_columns
        ):
            op.create_index(
                "idx_assignment_activity_user_session",
                "assignment_session_activity",
                ["user_id", "session_number"],
            )


def downgrade() -> None:
    # Check if table exists and what columns/indexes it has (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "assignment_session_activity" in existing_tables:
        existing_columns = [
            col["name"] for col in inspector.get_columns("assignment_session_activity")
        ]
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("assignment_session_activity")
        ]

        # Drop new index if it exists
        if "idx_assignment_activity_user_session" in existing_indexes:
            op.drop_index(
                "idx_assignment_activity_user_session",
                table_name="assignment_session_activity",
            )

        # Rename session_number back to attempt_number if session_number exists and attempt_number doesn't
        if (
            "session_number" in existing_columns
            and "attempt_number" not in existing_columns
        ):
            with op.batch_alter_table("assignment_session_activity") as batch_op:
                batch_op.alter_column(
                    "session_number", new_column_name="attempt_number"
                )

        # Recreate old index if it doesn't exist
        if (
            "idx_assignment_activity_user_attempt" not in existing_indexes
            and "attempt_number" in existing_columns
        ):
            op.create_index(
                "idx_assignment_activity_user_attempt",
                "assignment_session_activity",
                ["user_id", "attempt_number"],
            )
