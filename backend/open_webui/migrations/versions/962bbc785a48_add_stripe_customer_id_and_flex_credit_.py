"""Add stripe_customer_id and flex_credit_balance columns to company table, remove stripe_customer_id column from user table

Revision ID: 962bbc785a48
Revises: 6ae91e8c6b2f
Create Date: 2025-05-08 16:35:45.430931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '962bbc785a48'
down_revision: Union[str, None] = '6ae91e8c6b2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('user', 'stripe_customer_id')
    op.add_column('company', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('company', sa.Column('flex_credit_balance', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('company', 'stripe_customer_id')
    op.drop_column('company', 'flex_credit_balance')
    op.add_column('user', sa.Column('stripe_customer_id', sa.String(), nullable=True))
