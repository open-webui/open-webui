"""Add exit_quiz_response table

Revision ID: aa11bb22cc33
Revises: b07a8b94275e
Create Date: 2025-10-17 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "aa11bb22cc33"
down_revision = "b07a8b94275e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exit_quiz_response",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("child_id", sa.Text(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("score", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    op.create_index("idx_exit_quiz_user_id", "exit_quiz_response", ["user_id"]) 
    op.create_index("idx_exit_quiz_child_id", "exit_quiz_response", ["child_id"]) 
    op.create_index("idx_exit_quiz_created_at", "exit_quiz_response", ["created_at"]) 


def downgrade():
    op.drop_index("idx_exit_quiz_created_at", table_name="exit_quiz_response")
    op.drop_index("idx_exit_quiz_child_id", table_name="exit_quiz_response")
    op.drop_index("idx_exit_quiz_user_id", table_name="exit_quiz_response")
    op.drop_table("exit_quiz_response")


