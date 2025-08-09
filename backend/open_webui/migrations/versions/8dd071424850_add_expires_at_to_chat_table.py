"""add expires_at to chat table

Revision ID: 8dd071424850
Revises: 79fba6b72c04
Create Date: 2025-08-08 22:21:40.816447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dd071424850'
down_revision: Union[str, None] = '79fba6b72c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat', sa.Column('expires_at', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat', 'expires_at')