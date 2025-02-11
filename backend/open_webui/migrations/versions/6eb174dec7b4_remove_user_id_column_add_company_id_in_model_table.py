"""Remove user_id column, add company_id column in model table

Revision ID: 6eb174dec7b4
Revises: 9ca43b058511
Create Date: 2025-02-10 16:14:39.127920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '6eb174dec7b4'
down_revision: Union[str, None] = '9ca43b058511'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)


def upgrade() -> None:
    # Add company_id column if it doesn't exist
    if not column_exists("model", "company_id"):
        op.add_column('model', sa.Column('company_id', sa.String(), nullable=True))

    # Make columns non-nullable
    with op.batch_alter_table('model', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)

        # Delete user_id column if it exists
        if column_exists("model", "user_id"):
            batch_op.drop_column('user_id')

    # Add foreign key constraint if it doesn't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    foreign_keys = inspector.get_foreign_keys('model')
    if not any(fk['referred_table'] == 'company' for fk in foreign_keys):
        with op.batch_alter_table('model', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_user_company_id', 'company',
                ['company_id'], ['id'], ondelete='CASCADE'
            )


def downgrade() -> None:
    with op.batch_alter_table('model', schema=None) as batch_op:
        # Remove foreign key constraint if it exists
        foreign_keys = Inspector.from_engine(op.get_bind()).get_foreign_keys('model')
        if any(fk['name'] == 'fk_user_company_id' for fk in foreign_keys):
            batch_op.drop_constraint('fk_user_company_id', type_='foreignkey')

        # Drop columns if they exist
        if column_exists("model", "company_id"):
            batch_op.drop_column('company_id')

        # Add back user_id column if it doesn't exist
        if not column_exists("model", "user_id"):
            batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
