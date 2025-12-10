"""Add tenant_rebuild_schedule table

Revision ID: e6e6f4c2d451
Revises: bc3c0cc2e7ba
Create Date: 2025-12-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "e6e6f4c2d451"
down_revision = "bc3c0cc2e7ba"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenant_rebuild_schedule",
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column(
            "interval_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
        sa.Column("next_run", sa.DateTime(), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id"),
    )


def downgrade():
    op.drop_table("tenant_rebuild_schedule")
