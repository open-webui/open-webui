"""add_prompt_performance_indexes

Revision ID: 5251af02c082
Revises: 118d4ef0454d
Create Date: 2025-07-15 13:16:01.980287

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5251af02c082"
down_revision: Union[str, None] = "118d4ef0454d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add performance indexes for the prompt table
    # These indexes optimize common query patterns for pagination and search

    # Index for ordering by creation time (most common sort)
    op.create_index("idx_prompt_timestamp", "prompt", ["timestamp"], unique=False)

    # Index for filtering by user (permission-based queries)
    op.create_index("idx_prompt_user_id", "prompt", ["user_id"], unique=False)

    # Composite index for user-specific pagination (user_id + timestamp)
    op.create_index(
        "idx_prompt_user_timestamp", "prompt", ["user_id", "timestamp"], unique=False
    )

    # Index for search functionality on title
    op.create_index("idx_prompt_title_search", "prompt", ["title"], unique=False)

    # Note: command index not needed - prompt_command (UNIQUE) already exists


def downgrade() -> None:
    # Remove all the performance indexes
    op.drop_index("idx_prompt_title_search", table_name="prompt")
    op.drop_index("idx_prompt_user_timestamp", table_name="prompt")
    op.drop_index("idx_prompt_user_id", table_name="prompt")
    op.drop_index("idx_prompt_timestamp", table_name="prompt")
