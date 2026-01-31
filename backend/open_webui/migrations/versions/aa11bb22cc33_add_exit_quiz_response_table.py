"""Add exit_quiz_response table

Revision ID: aa11bb22cc33
Revises: b07a8b94275e
Create Date: 2024-12-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "aa11bb22cc33"
down_revision = "b07a8b94275e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "exit_quiz_response" not in existing_tables:
        # Create exit_quiz_response table
        op.create_table(
            "exit_quiz_response",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("child_id", sa.String(), nullable=True),
            sa.Column("question_key", sa.String(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=True),
            sa.Column("score", sa.JSON(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes for efficient querying
        op.create_index("idx_exit_quiz_user_id", "exit_quiz_response", ["user_id"])
        op.create_index("idx_exit_quiz_child_id", "exit_quiz_response", ["child_id"])
        op.create_index(
            "idx_exit_quiz_created_at", "exit_quiz_response", ["created_at"]
        )
    else:
        # Table exists, check if indexes exist
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("exit_quiz_response")
        ]
        indexes_to_create = [
            ("idx_exit_quiz_user_id", ["user_id"]),
            ("idx_exit_quiz_child_id", ["child_id"]),
            ("idx_exit_quiz_created_at", ["created_at"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "exit_quiz_response", columns)


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "exit_quiz_response" in existing_tables:
        # Drop indexes
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("exit_quiz_response")
        ]
        indexes_to_drop = [
            "idx_exit_quiz_created_at",
            "idx_exit_quiz_child_id",
            "idx_exit_quiz_user_id",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="exit_quiz_response")

        # Drop table
        op.drop_table("exit_quiz_response")
