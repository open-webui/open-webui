"""add child_email to child_profile

Revision ID: s55t66u77v88
Revises: df887c71f080
Create Date: 2026-01-31 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "s55t66u77v88"
down_revision = "df887c71f080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add child_email column to child_profile for storing child account email."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    existing_tables = inspector.get_table_names()
    if "child_profile" not in existing_tables:
        return

    existing_columns = [col["name"] for col in inspector.get_columns("child_profile")]
    if "child_email" not in existing_columns:
        with op.batch_alter_table("child_profile") as batch_op:
            batch_op.add_column(
                sa.Column("child_email", sa.String(), nullable=True)
            )


def downgrade() -> None:
    """Remove child_email column from child_profile."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    existing_tables = inspector.get_table_names()
    if "child_profile" not in existing_tables:
        return

    existing_columns = [col["name"] for col in inspector.get_columns("child_profile")]
    if "child_email" in existing_columns:
        with op.batch_alter_table("child_profile") as batch_op:
            batch_op.drop_column("child_email")
