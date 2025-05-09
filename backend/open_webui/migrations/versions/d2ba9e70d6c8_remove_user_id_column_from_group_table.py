"""Remove user_id column from group table

Revision ID: d2ba9e70d6c8
Revises: f1317dedd8e6
Create Date: 2025-05-06 09:15:07.771759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'd2ba9e70d6c8'
down_revision: Union[str, None] = 'f1317dedd8e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column('group', 'user_id')


def downgrade() -> None:
    op.add_column('group', sa.Column('user_id', sa.Text(), nullable=True))
