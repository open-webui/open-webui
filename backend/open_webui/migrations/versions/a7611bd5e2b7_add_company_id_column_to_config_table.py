"""Add company_id column to config table

Revision ID: a7611bd5e2b7
Revises: 2e6eee3a2c33
Create Date: 2025-05-02 11:43:27.976264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'a7611bd5e2b7'
down_revision: Union[str, None] = '2e6eee3a2c33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)

def upgrade() -> None:
    # Add company_id column if it doesn't exist
    if not column_exists("config", "company_id"):
        op.add_column('config', sa.Column('company_id', sa.String(), nullable=False, server_default="DEFAULT"))

    # Add foreign key constraint if it doesn't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    foreign_keys = inspector.get_foreign_keys('config')
    if not any(fk['referred_table'] == 'company' for fk in foreign_keys):
        with op.batch_alter_table('config', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_config_company_id', 'company',
                ['company_id'], ['id'], ondelete='CASCADE'
            )


def downgrade() -> None:
    with op.batch_alter_table('config', schema=None) as batch_op:
        # Remove foreign key constraint if it exists
        foreign_keys = Inspector.from_engine(op.get_bind()).get_foreign_keys('config')
        if any(fk['name'] == 'fk_config_company_id' for fk in foreign_keys):
            batch_op.drop_constraint('fk_config_company_id', type_='foreignkey')

        # Drop columns if they exist
        if column_exists("config", "company_id"):
            batch_op.drop_column('company_id')
