"""Add default language to user

Revision ID: d8c6f6c0f4b0
Revises: 018012973d35
Create Date: 2025-08-14 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "d8c6f6c0f4b0"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "default_language",
            sa.String(length=10),
            nullable=False,
            server_default="en-US",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "default_language")
