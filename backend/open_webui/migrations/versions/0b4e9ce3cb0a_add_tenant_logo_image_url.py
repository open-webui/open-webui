"""add tenant logo image url

Revision ID: 0b4e9ce3cb0a
Revises: b52eb7b69dc1
Create Date: 2025-03-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b4e9ce3cb0a"
down_revision: Union[str, None] = "b52eb7b69dc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("logo_image_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant", "logo_image_url")
