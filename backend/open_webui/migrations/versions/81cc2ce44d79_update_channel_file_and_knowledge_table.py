"""Update channel file and knowledge table

Revision ID: 81cc2ce44d79
Revises: 6283dc0e4d8d
Create Date: 2025-12-10 16:07:58.001282

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

# revision identifiers, used by Alembic.
revision: str = "81cc2ce44d79"
down_revision: Union[str, None] = "6283dc0e4d8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add message_id column to channel_file table
    with op.batch_alter_table("channel_file", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "message_id",
                sa.Text(),
                sa.ForeignKey(
                    "message.id", ondelete="CASCADE", name="fk_channel_file_message_id"
                ),
                nullable=True,
            )
        )

    # Add data column to knowledge table
    with op.batch_alter_table("knowledge", schema=None) as batch_op:
        batch_op.add_column(sa.Column("data", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove message_id column from channel_file table
    with op.batch_alter_table("channel_file", schema=None) as batch_op:
        batch_op.drop_column("message_id")

    # Remove data column from knowledge table
    with op.batch_alter_table("knowledge", schema=None) as batch_op:
        batch_op.drop_column("data")
