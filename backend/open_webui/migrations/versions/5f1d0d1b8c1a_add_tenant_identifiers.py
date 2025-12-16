"""Add tenant table-name and system-config client name columns

Revision ID: 5f1d0d1b8c1a
Revises: f26e8d0a0c85
Create Date: 2024-05-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "5f1d0d1b8c1a"
down_revision = "f26e8d0a0c85"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenant",
        sa.Column("table_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenant",
        sa.Column(
            "system_config_client_name",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("tenant", "system_config_client_name")
    op.drop_column("tenant", "table_name")
