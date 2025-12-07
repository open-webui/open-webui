"""merge billing and reply_to heads

Revision ID: 607801a77d0d
Revises: a5c220713937, e5f8a9b3c2d1
Create Date: 2025-12-05 03:12:14.859612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '607801a77d0d'
down_revision: Union[str, None] = ('a5c220713937', 'e5f8a9b3c2d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
