"""Merge migration heads after upstream pull

Revision ID: 2593db42b949
Revises: a5c220713937, b1c2d3e4f5a6
Create Date: 2025-10-09 22:47:05.511474

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '2593db42b949'
down_revision: Union[str, None] = ('a5c220713937', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
