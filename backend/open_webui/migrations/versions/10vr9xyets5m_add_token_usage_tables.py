"""Add token usage tables

Revision ID: 10vr9xyets5m
Revises: 9f0c9cd09105
Create Date: 2025-08-08 04:21:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "10vr9xyets5m"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Create token_group table
    op.create_table(
        "token_group",
        sa.Column("name", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("models", sa.JSON(), nullable=True),
        sa.Column("limit", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    # Create token_usage table
    op.create_table(
        "token_usage",
        sa.Column("group_name", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("token_in", sa.BigInteger(), nullable=True, default=0),
        sa.Column("token_out", sa.BigInteger(), nullable=True, default=0),
        sa.Column("token_total", sa.BigInteger(), nullable=True, default=0),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("token_usage")
    op.drop_table("token_group")