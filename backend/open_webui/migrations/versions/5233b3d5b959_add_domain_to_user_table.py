"""add domain to user table

Revision ID: 5233b3d5b959
Revises: 3781e22d8b01
Create Date: 2025-04-01 10:45:28.890543

"""

from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5233b3d5b959"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("domain", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE user 
        SET domain = substr(email, instr(email, '@') + 1)
        WHERE domain IS NULL
    """
    )


def downgrade() -> None:
    op.drop_column("user", "domain")
