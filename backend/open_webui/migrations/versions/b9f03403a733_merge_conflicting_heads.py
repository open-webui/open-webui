"""merge conflicting heads

Revision ID: b9f03403a733
Revises: 38d63c18f30f, <REPLACE_WITH_NEW_ID>
Create Date: 2025-09-24 23:21:06.424390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'b9f03403a733'
down_revision: Union[str, None] = ('38d63c18f30f', '<REPLACE_WITH_NEW_ID>')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
