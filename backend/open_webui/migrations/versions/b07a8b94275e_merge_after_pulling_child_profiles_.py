"""Merge after pulling child profiles feature

Revision ID: b07a8b94275e
Revises: 2593db42b949, f2g3h4i5j6k7
Create Date: 2025-10-09 22:50:59.799366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'b07a8b94275e'
down_revision: Union[str, None] = ('2593db42b949', 'f2g3h4i5j6k7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
