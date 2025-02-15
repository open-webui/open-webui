"""Add channel table

Revision ID: 57c599a3cb57
Revises: 922e7a387820
Create Date: 2024-12-22 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "57c599a3cb57"
down_revision = "922e7a387820"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "channel",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text()),
        sa.Column("name", sa.Text()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    op.create_table(
        "message",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text()),
        sa.Column("channel_id", sa.Text(), nullable=True),
        sa.Column("content", sa.Text()),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("channel")

    op.drop_table("message")
