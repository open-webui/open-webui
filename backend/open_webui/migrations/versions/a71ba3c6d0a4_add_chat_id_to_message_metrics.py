"""add_chat_id_to_message_metrics

Revision ID: a71ba3c6d0a4
Revises: ed37e461f285
Create Date: 2025-08-19 21:42:50.668694

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = "a71ba3c6d0a4"
down_revision: Union[str, None] = "ed37e461f285"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chat_id column to message_metrics table
    op.add_column("message_metrics", sa.Column("chat_id", sa.Text, nullable=True))


def downgrade() -> None:
    # Remove chat_id column from message_metrics table
    op.drop_column("message_metrics", "chat_id")
