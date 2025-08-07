"""add_feedback_performance_indexes

Revision ID: ed37e461f285
Revises: 5251af02c082
Create Date: 2025-07-15 13:16:11.337449

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ed37e461f285"
down_revision: Union[str, None] = "5251af02c082"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add performance indexes for the feedback table
    # These indexes optimize common query patterns for pagination and search

    # Index for ordering by creation time (most common sort)
    op.create_index("idx_feedback_created_at", "feedback", ["created_at"], unique=False)

    # Index for filtering by user (permission-based queries)
    op.create_index("idx_feedback_user_id", "feedback", ["user_id"], unique=False)

    # Composite index for user-specific pagination (user_id + created_at)
    op.create_index(
        "idx_feedback_user_created_at",
        "feedback",
        ["user_id", "created_at"],
        unique=False,
    )

    # Index for filtering by feedback type
    op.create_index("idx_feedback_type", "feedback", ["type"], unique=False)

    # Index for filtering by version
    op.create_index("idx_feedback_version", "feedback", ["version"], unique=False)


def downgrade() -> None:
    # Remove all the performance indexes
    op.drop_index("idx_feedback_version", table_name="feedback")
    op.drop_index("idx_feedback_type", table_name="feedback")
    op.drop_index("idx_feedback_user_created_at", table_name="feedback")
    op.drop_index("idx_feedback_user_id", table_name="feedback")
    op.drop_index("idx_feedback_created_at", table_name="feedback")
