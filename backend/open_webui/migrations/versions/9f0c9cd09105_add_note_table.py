"""Add note table

Revision ID: 9f0c9cd09105
Revises: 3781e22d8b01
Create Date: 2024-12-30 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "9f0c9cd09105"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "note" not in existing_tables:
        op.create_table(
            "note",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text()),
            sa.Column("title", sa.Text()),
            sa.Column("data", sa.JSON()),
            sa.Column("meta", sa.JSON()),
            sa.Column("access_control", sa.JSON()),
            sa.Column("created_at", sa.BigInteger()),
            sa.Column("updated_at", sa.BigInteger()),
        )


def downgrade():
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "note" in existing_tables:
        op.drop_table("note")
