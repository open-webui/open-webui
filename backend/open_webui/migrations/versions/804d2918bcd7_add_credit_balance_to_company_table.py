"""Add credit_balance to company table

Revision ID: 804d2918bcd7
Revises: 6eb174dec7b4
Create Date: 2025-02-13 15:57:15.692481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '804d2918bcd7'
down_revision: Union[str, None] = '6eb174dec7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)

def upgrade() -> None:
    # Add company_id column if it doesn't exist
    if not column_exists("company", "credit_balance"):
        op.add_column('company', sa.Column('credit_balance', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('company', schema=None) as batch_op:
        if column_exists("company", "credit_balance"):
            batch_op.drop_column('credit_balance')
