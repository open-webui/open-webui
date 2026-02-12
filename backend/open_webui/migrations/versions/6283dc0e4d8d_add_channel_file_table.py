"""Add channel file table

Revision ID: 6283dc0e4d8d
Revises: 3e0e00844bb0
Create Date: 2025-12-10 15:11:39.424601

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

# revision identifiers, used by Alembic.
revision: str = "6283dc0e4d8d"
down_revision: Union[str, None] = "3e0e00844bb0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_file",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "channel_id",
            sa.Text(),
            sa.ForeignKey("channel.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            sa.Text(),
            sa.ForeignKey("file.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        # indexes
        sa.Index("ix_channel_file_channel_id", "channel_id"),
        sa.Index("ix_channel_file_file_id", "file_id"),
        sa.Index("ix_channel_file_user_id", "user_id"),
        # unique constraints
        sa.UniqueConstraint(
            "channel_id", "file_id", name="uq_channel_file_channel_file"
        ),  # prevent duplicate entries
    )


def downgrade() -> None:
    op.drop_table("channel_file")
