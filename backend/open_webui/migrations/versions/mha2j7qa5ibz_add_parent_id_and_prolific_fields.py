"""add_parent_id_and_prolific_fields

Revision ID: mha2j7qa5ibz
Revises: 38d63c18f30f
Create Date: 2025-01-09 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "mha2j7qa5ibz"
down_revision: Union[str, None] = "38d63c18f30f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parent_id column and prolific fields to user table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    existing_columns = [col["name"] for col in inspector.get_columns("user")]

    # Add prolific fields if they don't exist
    if "prolific_pid" not in existing_columns:
        op.add_column(
            "user", sa.Column("prolific_pid", sa.String(), nullable=True, unique=True)
        )

    if "study_id" not in existing_columns:
        op.add_column("user", sa.Column("study_id", sa.String(), nullable=True))

    if "current_session_id" not in existing_columns:
        op.add_column(
            "user", sa.Column("current_session_id", sa.String(), nullable=True)
        )

    if "session_number" not in existing_columns:
        op.add_column(
            "user",
            sa.Column(
                "session_number", sa.BigInteger(), nullable=False, server_default="1"
            ),
        )

    if "consent_given" not in existing_columns:
        op.add_column("user", sa.Column("consent_given", sa.Boolean(), nullable=True))

    # Add parent_id column for child accounts
    if "parent_id" not in existing_columns:
        op.add_column("user", sa.Column("parent_id", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove parent_id and prolific fields from user table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    existing_columns = [col["name"] for col in inspector.get_columns("user")]

    if "parent_id" in existing_columns:
        op.drop_column("user", "parent_id")

    if "consent_given" in existing_columns:
        op.drop_column("user", "consent_given")

    if "session_number" in existing_columns:
        op.drop_column("user", "session_number")

    if "current_session_id" in existing_columns:
        op.drop_column("user", "current_session_id")

    if "study_id" in existing_columns:
        op.drop_column("user", "study_id")

    if "prolific_pid" in existing_columns:
        op.drop_column("user", "prolific_pid")
