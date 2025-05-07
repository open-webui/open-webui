"""Add company_id column to knowlege table

Revision ID: 6ae91e8c6b2f
Revises: d2ba9e70d6c8
Create Date: 2025-05-06 13:24:12.157418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '6ae91e8c6b2f'
down_revision: Union[str, None] = 'd2ba9e70d6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('knowledge', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.String(), nullable=False))
        batch_op.create_foreign_key('fk_knowledge_company_id', 'company', ['company_id'], ['id'])

def downgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('knowledge', schema=None) as batch_op:
        batch_op.drop_constraint('fk_knowledge_company_id', type_='foreignkey')
        batch_op.drop_column('company_id')
