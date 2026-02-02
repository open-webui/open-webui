"""Update channel and channel members table

Revision ID: 90ef40d4714e
Revises: b10670c03dd5
Create Date: 2025-11-30 06:33:38.790341

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
import open_webui.internal.db

# revision identifiers, used by Alembic.
revision: str = "90ef40d4714e"
down_revision: Union[str, None] = "b10670c03dd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # Update 'channel' table (idempotent)
    if "channel" in existing_tables:
        channel_columns = [col["name"] for col in inspector.get_columns("channel")]

        if "is_private" not in channel_columns:
            op.add_column("channel", sa.Column("is_private", sa.Boolean(), nullable=True))
        if "archived_at" not in channel_columns:
            op.add_column("channel", sa.Column("archived_at", sa.BigInteger(), nullable=True))
        if "archived_by" not in channel_columns:
            op.add_column("channel", sa.Column("archived_by", sa.Text(), nullable=True))
        if "deleted_at" not in channel_columns:
            op.add_column("channel", sa.Column("deleted_at", sa.BigInteger(), nullable=True))
        if "deleted_by" not in channel_columns:
            op.add_column("channel", sa.Column("deleted_by", sa.Text(), nullable=True))
        if "updated_by" not in channel_columns:
            op.add_column("channel", sa.Column("updated_by", sa.Text(), nullable=True))

    # Update 'channel_member' table (idempotent)
    if "channel_member" in existing_tables:
        member_columns = [col["name"] for col in inspector.get_columns("channel_member")]

        if "role" not in member_columns:
            op.add_column("channel_member", sa.Column("role", sa.Text(), nullable=True))
        if "invited_by" not in member_columns:
            op.add_column("channel_member", sa.Column("invited_by", sa.Text(), nullable=True))
        if "invited_at" not in member_columns:
            op.add_column("channel_member", sa.Column("invited_at", sa.BigInteger(), nullable=True))

    #  Create 'channel_webhook' table (idempotent)
    if "channel_webhook" not in existing_tables:
        op.create_table(
            "channel_webhook",
            sa.Column("id", sa.Text(), primary_key=True, unique=True, nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column(
                "channel_id",
                sa.Text(),
                sa.ForeignKey("channel.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("profile_image_url", sa.Text(), nullable=True),
            sa.Column("token", sa.Text(), nullable=False),
            sa.Column("last_used_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    pass


def downgrade() -> None:
    # Downgrade 'channel' table
    op.drop_column("channel", "is_private")
    op.drop_column("channel", "archived_at")
    op.drop_column("channel", "archived_by")
    op.drop_column("channel", "deleted_at")
    op.drop_column("channel", "deleted_by")
    op.drop_column("channel", "updated_by")

    # Downgrade 'channel_member' table
    op.drop_column("channel_member", "role")
    op.drop_column("channel_member", "invited_by")
    op.drop_column("channel_member", "invited_at")

    # Drop 'channel_webhook' table
    op.drop_table("channel_webhook")

    pass
