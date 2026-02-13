"""Add chat_user_view table

Revision ID: f8d6a5e2b1c3
Revises: c440947495f3
Create Date: 2026-02-12 01:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8d6a5e2b1c3"
down_revision: Union[str, None] = "c440947495f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_user_view",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "chat_id",
            sa.Text(),
            sa.ForeignKey("chat.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_viewed_at", sa.BigInteger(), nullable=False),
        sa.Index("idx_chat_user_view_user_chat", "user_id", "chat_id", unique=True),
        sa.Index("idx_chat_user_view_user_id", "user_id"),
        sa.Index("idx_chat_user_view_chat_id", "chat_id"),
    )


def downgrade() -> None:
    op.drop_table("chat_user_view")
