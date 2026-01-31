"""add_duration_seconds_to_scenario_assignments

Revision ID: q33r44s55t66
Revises: a02a9745bf68
Create Date: 2025-01-XX 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "q33r44s55t66"
down_revision = "a02a9745bf68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add duration_seconds column to scenario_assignments table"""
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "scenario_assignments" in existing_tables:
        existing_columns = [
            col["name"] for col in inspector.get_columns("scenario_assignments")
        ]
        if "duration_seconds" not in existing_columns:
            op.add_column(
                "scenario_assignments",
                sa.Column("duration_seconds", sa.Integer(), nullable=True),
            )


def downgrade() -> None:
    """Remove duration_seconds column from scenario_assignments table"""
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "scenario_assignments" in existing_tables:
        existing_columns = [
            col["name"] for col in inspector.get_columns("scenario_assignments")
        ]
        if "duration_seconds" in existing_columns:
            op.drop_column("scenario_assignments", "duration_seconds")
