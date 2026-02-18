"""Add current_attempt_number to user table

Revision ID: x00y11z22a33
Revises: w99x00y11z22
Create Date: 2026-02-13 00:00:00.000000

Stores the current attempt number after a workflow reset so new moderation
and exit_quiz rows use the incremented attempt.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "x00y11z22a33"
down_revision: Union[str, None] = "w99x00y11z22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("user")]
    if "current_attempt_number" not in columns:
        op.add_column(
            "user", sa.Column("current_attempt_number", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("user", "current_attempt_number")
