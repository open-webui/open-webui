"""Add copmany_id column to prompt and model table

Revision ID: 8bc701296ffa
Revises: 54243f6ae1ba
Create Date: 2025-04-14 10:13:46.354191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '8bc701296ffa'
down_revision: Union[str, None] = '54243f6ae1ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prompt', sa.Column('company_id', sa.String(), nullable=False))
    op.add_column('model', sa.Column('company_id', sa.String(), nullable=False))

    # Add foreign key constraint if it doesn't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    foreign_keys = inspector.get_foreign_keys('prompt')
    if not any(fk['referred_table'] == 'company' for fk in foreign_keys):
        with op.batch_alter_table('prompt', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_user_company_id', 'company',
                ['company_id'], ['id'], ondelete='CASCADE'
            )

    foreign_keys = inspector.get_foreign_keys('model')
    if not any(fk['referred_table'] == 'company' for fk in foreign_keys):
        with op.batch_alter_table('model', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_user_company_id', 'company',
                ['company_id'], ['id'], ondelete='CASCADE'
            )



def downgrade() -> None:
    op.drop_column('prompt', 'company_id')
    op.drop_column('model', 'company_id')

    with op.batch_alter_table('prompt', schema=None) as batch_op:
        # Remove foreign key constraint if it exists
        foreign_keys = Inspector.from_engine(op.get_bind()).get_foreign_keys('prompt')
        if any(fk['name'] == 'fk_user_company_id' for fk in foreign_keys):
            batch_op.drop_constraint('fk_user_company_id', type_='foreignkey')

    with op.batch_alter_table('model', schema=None) as batch_op:
        # Remove foreign key constraint if it exists
        foreign_keys = Inspector.from_engine(op.get_bind()).get_foreign_keys('model')
        if any(fk['name'] == 'fk_user_company_id' for fk in foreign_keys):
            batch_op.drop_constraint('fk_user_company_id', type_='foreignkey')
