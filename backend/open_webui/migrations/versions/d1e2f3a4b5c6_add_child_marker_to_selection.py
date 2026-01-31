"""Add child_marker column to selection table

Revision ID: d1e2f3a4b5c6
Revises: b1c2d3e4f5a6
Create Date: 2024-12-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        if "child_marker" not in selection_columns:
            op.add_column(
                "selection", sa.Column("child_marker", sa.String(), nullable=True)
            )


def downgrade() -> None:
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        if "child_marker" in selection_columns:
            op.drop_column("selection", "child_marker")
