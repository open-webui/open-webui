"""
Change assignment time tracking from attempt_number to session_number

Revision ID: m67n78o89p90
Revises: l67m78n89o90
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa

revision = "m67n78o89p90"
down_revision = "l67m78n89o90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing index
    op.drop_index("idx_assignment_activity_user_attempt", table_name="assignment_session_activity")
    
    # Rename column: attempt_number -> session_number
    with op.batch_alter_table("assignment_session_activity") as batch_op:
        batch_op.alter_column("attempt_number", new_column_name="session_number")
    
    # Create new index with session_number
    op.create_index(
        "idx_assignment_activity_user_session",
        "assignment_session_activity",
        ["user_id", "session_number"],
    )


def downgrade() -> None:
    # Drop the new index
    op.drop_index("idx_assignment_activity_user_session", table_name="assignment_session_activity")
    
    # Rename column back: session_number -> attempt_number
    with op.batch_alter_table("assignment_session_activity") as batch_op:
        batch_op.alter_column("session_number", new_column_name="attempt_number")
    
    # Recreate the old index
    op.create_index(
        "idx_assignment_activity_user_attempt",
        "assignment_session_activity",
        ["user_id", "attempt_number"],
    )



