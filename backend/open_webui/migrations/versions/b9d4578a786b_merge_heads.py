"""merge_heads

Revision ID: b9d4578a786b
Revises: aa11bb22cc33, ab12cd34ef56
Create Date: 2025-10-18 10:41:02.019013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'b9d4578a786b'
down_revision: Union[str, None] = ('aa11bb22cc33', 'ab12cd34ef56')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
