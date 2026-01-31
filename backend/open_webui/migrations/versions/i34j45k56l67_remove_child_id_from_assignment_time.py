"""Remove child_id from assignment_session_activity table

Revision ID: i34j45k56l67
Revises: h23i45j67k89
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "i34j45k56l67"
down_revision = "h23i45j67k89"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table and column exist (idempotent migration)
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

        # Drop index if it exists
        if "idx_assignment_activity_user_child_attempt" in existing_indexes:
            op.drop_index(
                "idx_assignment_activity_user_child_attempt",
                table_name="assignment_session_activity",
            )

        # Drop column if it exists
        if "child_id" in existing_columns:
            op.drop_column("assignment_session_activity", "child_id")


def downgrade() -> None:
    # Check if table exists before adding column back
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "assignment_session_activity" in existing_tables:
        existing_columns = [
            col["name"] for col in inspector.get_columns("assignment_session_activity")
        ]
        if "child_id" not in existing_columns:
            op.add_column(
                "assignment_session_activity",
                sa.Column("child_id", sa.Text(), nullable=True),
            )
