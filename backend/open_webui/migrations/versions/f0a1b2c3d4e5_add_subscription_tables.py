"""Add subscription tables

Revision ID: f0a1b2c3d4e5
Revises: 461111b60977
Create Date: 2026-06-03 06:00:00.000000

Adds tables for the USDT subscription system:
- subscription_tier         : admin-configurable tiers (price, daily limit, allowed models)
- user_subscription         : a user's granted subscription(s)
- subscription_order        : payment intents mapped to the Java payment_service order
- subscription_usage_daily  : per-user daily message counters (metering)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'subscription_tier' not in existing_tables:
        op.create_table(
            'subscription_tier',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('price_usd', sa.Float(), nullable=False, server_default='0'),
            sa.Column('duration_days', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('daily_message_limit', sa.Integer(), nullable=True),
            sa.Column('allowed_model_ids', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    if 'user_subscription' not in existing_tables:
        op.create_table(
            'user_subscription',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('tier_id', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='active'),
            sa.Column('started_at', sa.BigInteger(), nullable=False),
            sa.Column('expires_at', sa.BigInteger(), nullable=False),
            sa.Column('order_id', sa.String(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_user_subscription_user', 'user_subscription', ['user_id'])
        op.create_index('idx_user_subscription_expires', 'user_subscription', ['expires_at'])

    if 'subscription_order' not in existing_tables:
        op.create_table(
            'subscription_order',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('logical_order_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('tier_id', sa.String(), nullable=False),
            sa.Column('chain_id', sa.String(), nullable=False),
            sa.Column('amount', sa.String(), nullable=False),
            sa.Column('address', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
            sa.Column('tx_hash', sa.String(), nullable=True),
            sa.Column('activated', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('expires_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_subscription_order_user', 'subscription_order', ['user_id'])
        op.create_index('idx_subscription_order_logical', 'subscription_order', ['logical_order_id'])

    if 'subscription_usage_daily' not in existing_tables:
        op.create_table(
            'subscription_usage_daily',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('date', sa.String(), nullable=False),
            sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_subscription_usage_user', 'subscription_usage_daily', ['user_id'])


def downgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'subscription_usage_daily' in existing_tables:
        op.drop_index('idx_subscription_usage_user', table_name='subscription_usage_daily')
        op.drop_table('subscription_usage_daily')

    if 'subscription_order' in existing_tables:
        op.drop_index('idx_subscription_order_logical', table_name='subscription_order')
        op.drop_index('idx_subscription_order_user', table_name='subscription_order')
        op.drop_table('subscription_order')

    if 'user_subscription' in existing_tables:
        op.drop_index('idx_user_subscription_expires', table_name='user_subscription')
        op.drop_index('idx_user_subscription_user', table_name='user_subscription')
        op.drop_table('user_subscription')

    if 'subscription_tier' in existing_tables:
        op.drop_table('subscription_tier')
