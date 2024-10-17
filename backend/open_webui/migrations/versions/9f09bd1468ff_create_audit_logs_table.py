"""create audit logs table

Revision ID: 9f09bd1468ff
Revises: ca81bd47c050
Create Date: 2024-10-03 09:01:52.321774

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.apps.webui.internal.db
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "9f09bd1468ff"
down_revision: Union[str, None] = "6a39f3d8e55c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("log_level", sa.String(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("source_ip", sa.String(), nullable=True),
        sa.Column("object_id", sa.String(), nullable=True),
        sa.Column("object_type", sa.String(), nullable=True),
        sa.Column("admin_id", sa.String(), nullable=True),
        sa.Column("admin_api_key", sa.String(), nullable=True),
        sa.Column("request_uri", sa.String(), nullable=True),
        sa.Column("entry_expiration_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("request_info", sa.JSON(), nullable=True),
        sa.Column("response_info", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
