"""Add eula_signed_at to user

Revision ID: 2e91d6c25ecd
Revises: 7bd26b4a8c12
Create Date: 2025-03-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2e91d6c25ecd"
down_revision: Union[str, None] = "7bd26b4a8c12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("eula_signed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "eula_signed_at")
