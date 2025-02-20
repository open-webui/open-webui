"""Create stripe_customer_id column to user table

Revision ID: 44d3227ecc28
Revises: 44f99b8dae57
Create Date: 2025-02-19 16:24:59.173033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '44d3227ecc28'
down_revision: Union[str, None] = '44f99b8dae57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)


def upgrade() -> None:
    # Add stripe_customer_id column if it doesn't exist
    if not column_exists("user", "stripe_customer_id"):
        op.add_column('user', sa.Column('stripe_customer_id', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        if column_exists("user", "stripe_customer_id"):
            batch_op.drop_column('stripe_customer_id')

