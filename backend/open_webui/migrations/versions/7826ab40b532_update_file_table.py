"""Update file table

Revision ID: 7826ab40b532
Revises: 57c599a3cb57
Create Date: 2024-12-23 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "7826ab40b532"
down_revision = "57c599a3cb57"
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    file_columns = [col["name"] for col in inspector.get_columns("file")]
    
    if "access_control" not in file_columns:
        op.add_column(
            "file",
            sa.Column("access_control", sa.JSON(), nullable=True),
        )


def downgrade():
    op.drop_column("file", "access_control")
