"""Add password_reset_token and password_reset_token_expires_at to user table

Revision ID: d56ab8c77cf7
Revises: 05d6d7fcdffe
Create Date: 2025-04-29 11:30:27.772557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'd56ab8c77cf7'
down_revision: Union[str, None] = '05d6d7fcdffe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('password_reset_token', sa.String(), nullable=True))
    op.add_column('user', sa.Column('password_reset_token_expires_at', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'password_reset_token')
    op.drop_column('user', 'password_reset_token_expires_at')

