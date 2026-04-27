"""Add attempts table for problem-solving evaluation

Revision ID: add_attempts_table
Revises: add_prompt_group_tables, add_rag_chapter_detection
Create Date: 2026-04-27

Merges two heads and adds the `attempts` table:
- Records each problem-solving attempt by a user
- Links to the Langfuse trace_id for cross-referencing scores
"""

from alembic import op
import sqlalchemy as sa

revision = "add_attempts_table"
down_revision = ("add_prompt_group_tables", "add_rag_chapter_detection")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("problem_id", sa.String(), nullable=True),
        sa.Column("chapter_id", sa.String(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )

    op.create_index("idx_attempts_user", "attempts", ["user_id"])
    op.create_index("idx_attempts_problem", "attempts", ["problem_id"])
    op.create_index("idx_attempts_trace", "attempts", ["trace_id"])
    op.create_index("idx_attempts_created", "attempts", ["created_at"])


def downgrade():
    op.drop_index("idx_attempts_created", table_name="attempts")
    op.drop_index("idx_attempts_trace", table_name="attempts")
    op.drop_index("idx_attempts_problem", table_name="attempts")
    op.drop_index("idx_attempts_user", table_name="attempts")
    op.drop_table("attempts")
