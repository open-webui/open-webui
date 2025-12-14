"""Add tag_feedback table

Revision ID: add_tag_feedback_table
Revises: add_prompt_tool_fields
Create Date: 2025-01-04

This migration adds the tag_feedback table for user feedback on tags:
- user_id + tag_id: Composite primary key
- status: Feedback status (not_interested, understood, confused, or null)
"""

from alembic import op
import sqlalchemy as sa

revision = "add_tag_feedback_table"
down_revision = "add_prompt_tool_fields"
branch_labels = None
depends_on = None


def upgrade():
    # Create tag_feedback table with composite primary key
    op.create_table(
        "tag_feedback",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("tag_id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=True),  # not_interested, understood, confused
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create indexes
    op.create_index("idx_tag_feedback_user", "tag_feedback", ["user_id"])
    op.create_index("idx_tag_feedback_tag", "tag_feedback", ["tag_id"])


def downgrade():
    # Drop indexes
    op.drop_index("idx_tag_feedback_tag", table_name="tag_feedback")
    op.drop_index("idx_tag_feedback_user", table_name="tag_feedback")

    # Drop table
    op.drop_table("tag_feedback")
