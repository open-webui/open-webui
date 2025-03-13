"""Update message & channel tables

Revision ID: 3781e22d8b01
Revises: 7826ab40b532
Create Date: 2024-12-30 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "3781e22d8b01"
down_revision = "7826ab40b532"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'type' column to the 'channel' table
    op.add_column(
        "channel",
        sa.Column(
            "type",
            sa.Text(),
            nullable=True,
        ),
    )

    # Add 'parent_id' column to the 'message' table for threads
    op.add_column(
        "message",
        sa.Column("parent_id", sa.Text(), nullable=True),
    )

    op.create_table(
        "message_reaction",
        sa.Column(
            "id", sa.Text(), nullable=False, primary_key=True, unique=True
        ),  # Unique reaction ID
        sa.Column("user_id", sa.Text(), nullable=False),  # User who reacted
        sa.Column(
            "message_id", sa.Text(), nullable=False
        ),  # Message that was reacted to
        sa.Column(
            "name", sa.Text(), nullable=False
        ),  # Reaction name (e.g. "thumbs_up")
        sa.Column(
            "created_at", sa.BigInteger(), nullable=True
        ),  # Timestamp of when the reaction was added
    )

    op.create_table(
        "channel_member",
        sa.Column(
            "id", sa.Text(), nullable=False, primary_key=True, unique=True
        ),  # Record ID for the membership row
        sa.Column("channel_id", sa.Text(), nullable=False),  # Associated channel
        sa.Column("user_id", sa.Text(), nullable=False),  # Associated user
        sa.Column(
            "created_at", sa.BigInteger(), nullable=True
        ),  # Timestamp of when the user joined the channel
    )


def downgrade():
    # Revert 'type' column addition to the 'channel' table
    op.drop_column("channel", "type")
    op.drop_column("message", "parent_id")
    op.drop_table("message_reaction")
    op.drop_table("channel_member")
