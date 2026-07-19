"""add katalog fields to knowledge

Revision ID: 7e4d1a9c2b83
Revises: 461111b60977
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7e4d1a9c2b83'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('knowledge', sa.Column('ai_overwiew', sa.Text(), nullable=True))
    op.add_column('knowledge', sa.Column('registration_number', sa.Text(), nullable=True))
    op.add_column('knowledge', sa.Column('registration_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('knowledge', 'registration_date')
    op.drop_column('knowledge', 'registration_number')
    op.drop_column('knowledge', 'ai_overwiew')
