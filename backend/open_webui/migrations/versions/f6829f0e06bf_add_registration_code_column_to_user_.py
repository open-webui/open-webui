"""Add registration_code column to user table

Revision ID: f6829f0e06bf
Revises: d56ab8c77cf7
Create Date: 2025-04-29 16:02:56.017491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'f6829f0e06bf'
down_revision: Union[str, None] = 'd56ab8c77cf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('registration_code', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'registration_code')

