"""Add enable_pii_detection to knowledge table

Revision ID: aac72a474c6b
Revises: d31026856c01
Create Date: 2024-12-19 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "aac72a474c6b"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'enable_pii_detection' column to 'knowledge' table
    op.add_column(
        "knowledge",
        sa.Column(
            "enable_pii_detection",
            sa.Boolean(),
            nullable=True,
            server_default=sa.sql.expression.false(),
        ),
    )


def downgrade():
    # Drop 'enable_pii_detection' column from 'knowledge' table
    op.drop_column("knowledge", "enable_pii_detection")
