"""Add attempt_number to scenario_assignments table

Revision ID: y11z22a33b44
Revises: x00y11z22a33
Create Date: 2026-02-13 00:00:00.000000

Adds attempt_number column to scenario_assignments to track which workflow
attempt each assignment belongs to. Assignments are now filtered by the
current attempt number, so after a reset users get new assignments for the new attempt.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "y11z22a33b44"
down_revision: Union[str, None] = "x00y11z22a33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "scenario_assignments" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("scenario_assignments")]
    if "attempt_number" not in columns:
        # Add column with default value of 1 for existing rows
        op.add_column(
            "scenario_assignments",
            sa.Column(
                "attempt_number", sa.Integer(), nullable=False, server_default="1"
            ),
        )
        # Remove server_default after adding the column so new rows don't get default
        op.alter_column("scenario_assignments", "attempt_number", server_default=None)

    # Add indexes for efficient filtering
    existing_indexes = [
        idx["name"] for idx in inspector.get_indexes("scenario_assignments")
    ]
    if "idx_assignments_attempt_number" not in existing_indexes:
        op.create_index(
            "idx_assignments_attempt_number",
            "scenario_assignments",
            ["attempt_number"],
        )
    if "idx_assignments_child_attempt" not in existing_indexes:
        op.create_index(
            "idx_assignments_child_attempt",
            "scenario_assignments",
            ["child_profile_id", "attempt_number"],
        )


def downgrade() -> None:
    op.drop_index("idx_assignments_child_attempt", table_name="scenario_assignments")
    op.drop_index("idx_assignments_attempt_number", table_name="scenario_assignments")
    op.drop_column("scenario_assignments", "attempt_number")
