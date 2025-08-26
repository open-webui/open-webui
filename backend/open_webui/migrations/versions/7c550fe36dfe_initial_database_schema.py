"""Initial database schema

Revision ID: 7c550fe36dfe
Revises: 3af16a1c9fb6
Create Date: 2025-08-26 17:16:25.732807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '7c550fe36dfe'
down_revision: Union[str, None] = '3af16a1c9fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
