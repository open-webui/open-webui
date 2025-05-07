"""Add note table

Revision ID: 9f0c9cd09105
Revises: 3781e22d8b01
Create Date: 2025-05-03 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "9f0c9cd09105"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "note",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("note")
