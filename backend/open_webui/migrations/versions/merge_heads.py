"""merge heads

Revision ID: merge_heads_001
Revises: add_city_column_001, add_supabase_id_001
Create Date: 2024-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads_001'
down_revision = ('add_city_column_001', 'add_supabase_id_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 