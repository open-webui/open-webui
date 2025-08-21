"""update user table

Revision ID: 3af16a1c9fb6
Revises: 018012973d35
Create Date: 2025-08-21 02:07:18.078283

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3af16a1c9fb6"
down_revision: Union[str, None] = "018012973d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("user", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("gender", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "username")
    op.drop_column("user", "bio")
    op.drop_column("user", "gender")
    op.drop_column("user", "date_of_birth")
