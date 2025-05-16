"""Add budget_mail_80_sent, budget_mail_100_sent columns to company table

Revision ID: 1e74585dcf49
Revises: 962bbc785a48
Create Date: 2025-05-12 12:40:28.658901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '1e74585dcf49'
down_revision: Union[str, None] = '962bbc785a48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('company', sa.Column('budget_mail_80_sent', sa.Boolean(), nullable=True))
    op.add_column('company', sa.Column('budget_mail_100_sent', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('company', 'budget_mail_80_sent')
    op.drop_column('company', 'budget_mail_100_sent')

