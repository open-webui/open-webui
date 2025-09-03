"""add allowed_domains to groups table

Revision ID: 64d8cd268d63
Revises: a71ba3c6d0a4
Create Date: 2025-09-02 21:45:34.156835

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = "64d8cd268d63"
down_revision: Union[str, None] = "a71ba3c6d0a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add allowed_domains column to group table
    op.add_column("group", sa.Column("allowed_domains", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Drop allowed_domains column from group table
    op.drop_column("group", "allowed_domains")
