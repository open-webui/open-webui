"""Update folder table data

Revision ID: d31026856c01
Revises: 9f0c9cd09105
Create Date: 2024-12-30 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "d31026856c01"
down_revision = "9f0c9cd09105"
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "folder" in existing_tables:
        folder_columns = [col["name"] for col in inspector.get_columns("folder")]
        if "data" not in folder_columns:
            op.add_column("folder", sa.Column("data", sa.JSON(), nullable=True))


def downgrade():
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "folder" in existing_tables:
        folder_columns = [col["name"] for col in inspector.get_columns("folder")]
        if "data" in folder_columns:
            op.drop_column("folder", "data")
