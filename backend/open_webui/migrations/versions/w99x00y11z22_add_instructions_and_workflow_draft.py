"""Add instructions_completed_at and workflow_draft table

Revision ID: w99x00y11z22
Revises: v88w99x00y11
Create Date: 2026-02-13 00:00:00.000000

- instructions_completed_at on user: when user completed assignment instructions
- workflow_draft: stores exit survey and moderation drafts (replaces localStorage)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "w99x00y11z22"
down_revision: Union[str, None] = "v88w99x00y11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Add instructions_completed_at to user
    if "user" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("user")]
        if "instructions_completed_at" not in columns:
            op.add_column(
                "user",
                sa.Column("instructions_completed_at", sa.BigInteger(), nullable=True),
            )

    # Create workflow_draft table for exit survey and moderation drafts
    if "workflow_draft" not in inspector.get_table_names():
        op.create_table(
            "workflow_draft",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("child_id", sa.Text(), nullable=False),
            sa.Column(
                "draft_type", sa.Text(), nullable=False
            ),  # "exit_survey" | "moderation"
            sa.Column("data", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_workflow_draft_user_child_type",
            "workflow_draft",
            ["user_id", "child_id", "draft_type"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_table("workflow_draft")
    op.drop_column("user", "instructions_completed_at")
