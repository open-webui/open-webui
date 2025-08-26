"""merge heads

Revision ID: 14f6763df9ca
Revises: 3af16a1c9fb6, e1b2c3d4
Create Date: 2025-08-26 13:14:30.337954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '14f6763df9ca'
down_revision: Union[str, None] = ('3af16a1c9fb6', 'e1b2c3d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
