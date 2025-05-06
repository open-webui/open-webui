"""Add company_id column to group table

Revision ID: f1317dedd8e6
Revises: a7611bd5e2b7
Create Date: 2025-05-06 09:01:46.001923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'f1317dedd8e6'
down_revision: Union[str, None] = 'a7611bd5e2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.String(), nullable=False))
        batch_op.create_foreign_key('fk_group_company_id', 'company', ['company_id'], ['id'])

def downgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.drop_constraint('fk_group_company_id', type_='foreignkey')
        batch_op.drop_column('company_id')
