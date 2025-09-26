"""add export logs table

Revision ID: 83ccb5a729a3
Revises: a71ba3c6d0a4
Create Date: 2025-09-08 13:21:39.690093

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = "83ccb5a729a3"
down_revision: Union[str, None] = "a71ba3c6d0a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_logs",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("email_domain", sa.Text, nullable=False),
        sa.Column("export_timestamp", sa.BigInteger, nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False),
        sa.Column("date_range_start", sa.BigInteger, nullable=False),
        sa.Column("date_range_end", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.BigInteger, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("export_logs")
