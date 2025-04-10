"""Add prebuilt and description column to prompt table

Revision ID: d0d528b0ec66
Revises: e7227267897c
Create Date: 2025-04-08 13:50:26.899800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'd0d528b0ec66'
down_revision: Union[str, None] = 'e7227267897c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prompt', sa.Column('prebuilt', sa.Boolean(), nullable=True))
    op.add_column('prompt', sa.Column('description', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('prompt', 'prebuilt')
    op.drop_column('prompt', 'description')
