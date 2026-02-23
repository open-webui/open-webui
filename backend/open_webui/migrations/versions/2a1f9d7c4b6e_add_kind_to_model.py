"""Add kind column to model

Revision ID: 2a1f9d7c4b6e
Revises: b2c3d4e5f6a7
Create Date: 2026-02-23 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "2a1f9d7c4b6e"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "model",
        sa.Column("kind", sa.Text(), nullable=True, server_default="model"),
    )

    op.execute("UPDATE model SET kind = 'model' WHERE kind IS NULL")


def downgrade():
    op.drop_column("model", "kind")
