"""Add user profile fields

Revision ID: b52eb7b69dc1
Revises: 5f1d0d1b8c1a
Create Date: 2025-03-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "b52eb7b69dc1"
down_revision = "5f1d0d1b8c1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("job_title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("primary_location", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("job_description", sa.String(length=2500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "job_description")
    op.drop_column("user", "primary_location")
    op.drop_column("user", "job_title")
