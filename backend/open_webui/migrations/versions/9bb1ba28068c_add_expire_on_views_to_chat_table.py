"""add expire_on_views to chat table

Revision ID: 9bb1ba28068c
Revises: 8dd071424850
Create Date: 2025-08-09 00:17:21.862699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bb1ba28068c'
down_revision: Union[str, None] = '8dd071424850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat', sa.Column('expire_on_views', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat', 'expire_on_views')