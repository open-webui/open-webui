"""merge main and shared-chats-page branches

Revision ID: e32a8e081b4a
Revises: 018012973d35, 79fba6b72c04
Create Date: 2025-08-19 11:55:29.746585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'e32a8e081b4a'
down_revision: Union[str, None] = ('018012973d35', '79fba6b72c04')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
