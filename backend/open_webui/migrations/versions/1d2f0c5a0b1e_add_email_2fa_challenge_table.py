"""Add email 2FA challenge table

Revision ID: 1d2f0c5a0b1e
Revises: f26e8d0a0c85
Create Date: 2025-03-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "1d2f0c5a0b1e"
down_revision: Union[str, Sequence[str], None] = "f26e8d0a0c85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "email_2fa_challenge" not in existing_tables:
        op.create_table(
            "email_2fa_challenge",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("code_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_email_2fa_user_id",
            "email_2fa_challenge",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "idx_email_2fa_expires_at",
            "email_2fa_challenge",
            ["expires_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("idx_email_2fa_expires_at", table_name="email_2fa_challenge")
    op.drop_index("idx_email_2fa_user_id", table_name="email_2fa_challenge")
    op.drop_table("email_2fa_challenge")
