"""Replace child_marker with child_id (UUID)

Revision ID: f2g3h4i5j6k7
Revises: e1f2g3h4i5j6
Create Date: 2024-12-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "f2g3h4i5j6k7"
down_revision = "e1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        has_child_marker = "child_marker" in selection_columns
        has_child_id = "child_id" in selection_columns

        if has_child_marker and not has_child_id:
            # Rename child_marker to child_id
            op.alter_column("selection", "child_marker", new_column_name="child_id")
        elif has_child_marker and has_child_id:
            # Both exist - drop child_marker since child_id already exists
            op.drop_column("selection", "child_marker")
        # If only child_id exists or neither exists, do nothing


def downgrade() -> None:
    # Check if columns exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        has_child_id = "child_id" in selection_columns
        has_child_marker = "child_marker" in selection_columns

        if has_child_id and not has_child_marker:
            # Rename child_id back to child_marker
            op.alter_column("selection", "child_id", new_column_name="child_marker")
        elif has_child_id and has_child_marker:
            # Both exist - drop child_id
            op.drop_column("selection", "child_id")
