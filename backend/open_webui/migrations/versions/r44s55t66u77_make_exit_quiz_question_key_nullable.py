"""make_exit_quiz_question_key_nullable

Revision ID: r44s55t66u77
Revises: q33r44s55t66
Create Date: 2025-01-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "r44s55t66u77"
down_revision = "q33r44s55t66"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make question_key nullable in exit_quiz_response table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "exit_quiz_response" in existing_tables:
        exit_quiz_columns = [
            col["name"] for col in inspector.get_columns("exit_quiz_response")
        ]

        # Check if question_key column exists and is not nullable
        if "question_key" in exit_quiz_columns:
            # Make question_key nullable (use batch for SQLite compatibility)
            with op.batch_alter_table("exit_quiz_response") as batch_op:
                batch_op.alter_column("question_key", nullable=True)


def downgrade() -> None:
    """Make question_key NOT NULL in exit_quiz_response table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "exit_quiz_response" in existing_tables:
        exit_quiz_columns = [
            col["name"] for col in inspector.get_columns("exit_quiz_response")
        ]

        # Check if question_key column exists
        if "question_key" in exit_quiz_columns:
            # First, set any NULL values to a default value
            op.execute(
                """
                UPDATE exit_quiz_response 
                SET question_key = 'exit-survey' 
                WHERE question_key IS NULL
            """
            )

            # Then make it NOT NULL (use batch for SQLite compatibility)
            with op.batch_alter_table("exit_quiz_response") as batch_op:
                batch_op.alter_column("question_key", nullable=False)
