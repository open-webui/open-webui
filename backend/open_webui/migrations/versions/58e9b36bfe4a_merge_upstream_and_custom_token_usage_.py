"""merge upstream and custom token usage migrations

Revision ID: 58e9b36bfe4a
Revises: a5c220713937, e223b100ad81
Create Date: 2025-10-26 21:25:56.954038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '58e9b36bfe4a'
down_revision: Union[str, None] = ('a5c220713937', 'e223b100ad81')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
