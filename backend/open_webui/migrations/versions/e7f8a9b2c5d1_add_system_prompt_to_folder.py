"""Add system prompt to folder

Revision ID: e7f8a9b2c5d1
Revises: 9f0c9cd09105
Create Date: 2025-06-21 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b2c5d1'
down_revision: Union[str, None] = '9f0c9cd09105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('folder', sa.Column('system_prompt', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('folder', 'system_prompt')
