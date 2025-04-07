"""Add meta column to prompt table

Revision ID: e7227267897c
Revises: e0cd6c95cb25
Create Date: 2025-04-07 12:06:19.997065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'e7227267897c'
down_revision: Union[str, None] = 'e0cd6c95cb25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prompt', sa.Column('meta', open_webui.internal.db.JSONField(), nullable=True))


def downgrade() -> None:
    op.drop_column('prompt', 'meta')
