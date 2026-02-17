"""merge heads and add chat_version column

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7, f8d6a5e2b1c3
Create Date: 2026-02-17 15:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, tuple[str, ...], None] = ("b2c3d4e5f6a7", "f8d6a5e2b1c3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chat_version column for optimistic locking
    op.add_column(
        "chat",
        sa.Column("chat_version", sa.BigInteger(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("chat", "chat_version")
