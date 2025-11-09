"""
Remove child_id from assignment_session_activity table

Revision ID: i34j45k56l67
Revises: h23i45j67k89
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa

revision = "i34j45k56l67"
down_revision = "h23i45j67k89"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old index that includes child_id
    op.drop_index("idx_assignment_activity_user_child_attempt", table_name="assignment_session_activity")
    
    # Drop the child_id column
    op.drop_column("assignment_session_activity", "child_id")
    
    # Create new index without child_id
    op.create_index(
        "idx_assignment_activity_user_attempt",
        "assignment_session_activity",
        ["user_id", "attempt_number"],
    )


def downgrade() -> None:
    # Drop the new index
    op.drop_index("idx_assignment_activity_user_attempt", table_name="assignment_session_activity")
    
    # Re-add child_id column
    op.add_column(
        "assignment_session_activity",
        sa.Column("child_id", sa.Text(), nullable=True),
    )
    
    # Re-create the old index with child_id
    op.create_index(
        "idx_assignment_activity_user_child_attempt",
        "assignment_session_activity",
        ["user_id", "child_id", "attempt_number"],
    )





