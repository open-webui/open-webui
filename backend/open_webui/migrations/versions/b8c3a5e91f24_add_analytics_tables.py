"""add_analytics_tables

Revision ID: b8c3a5e91f24
Revises: 58e9b36bfe4a
Create Date: 2026-01-02 00:00:00.000000

This migration adds the analytics tables for the "Wrapped" feature:
- conversation_token_usage: Tracks token usage per chat conversation
- daily_token_usage: Aggregates daily token stats per user (for heatmaps)
- model_token_usage: Tracks usage per model per user (for breakdowns)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'b8c3a5e91f24'
down_revision: Union[str, None] = '58e9b36bfe4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _existing_indexes(table_name: str) -> set:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {idx['name'] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    tables = _existing_tables()

    # Create conversation_token_usage table
    # Tracks tokens per chat conversation, updated after each message
    if 'conversation_token_usage' not in tables:
        op.create_table(
            'conversation_token_usage',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('chat_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('model_id', sa.String(), nullable=True),
            sa.Column('total_input_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_output_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('last_input_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('last_output_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('message_count', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )

    conv_indexes = _existing_indexes('conversation_token_usage')
    if 'conv_token_user_idx' not in conv_indexes:
        op.create_index('conv_token_user_idx', 'conversation_token_usage', ['user_id'])
    if 'conv_token_chat_idx' not in conv_indexes:
        op.create_index('conv_token_chat_idx', 'conversation_token_usage', ['chat_id'], unique=True)
    if 'conv_token_total_idx' not in conv_indexes:
        op.create_index('conv_token_total_idx', 'conversation_token_usage', ['total_tokens'])

    # Create daily_token_usage table
    # Aggregates daily token usage per user for heatmaps
    if 'daily_token_usage' not in tables:
        op.create_table(
            'daily_token_usage',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('date', sa.String(), nullable=False),  # YYYY-MM-DD format
            sa.Column('total_input_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_output_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('conversation_count', sa.Integer(), nullable=True, default=0),
            sa.Column('message_count', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )

    daily_indexes = _existing_indexes('daily_token_usage')
    if 'daily_user_date_idx' not in daily_indexes:
        op.create_index('daily_user_date_idx', 'daily_token_usage', ['user_id', 'date'], unique=True)
    if 'daily_date_idx' not in daily_indexes:
        op.create_index('daily_date_idx', 'daily_token_usage', ['date'])
    if 'daily_total_idx' not in daily_indexes:
        op.create_index('daily_total_idx', 'daily_token_usage', ['total_tokens'])

    # Create model_token_usage table
    # Tracks per-model token usage, supports both per-user and global aggregations
    if 'model_token_usage' not in tables:
        op.create_table(
            'model_token_usage',
            sa.Column('id', sa.String(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.String(), nullable=True),  # NULL = global aggregate
            sa.Column('model_id', sa.String(), nullable=False),
            sa.Column('total_input_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_output_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
            sa.Column('conversation_count', sa.Integer(), nullable=True, default=0),
            sa.Column('message_count', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )

    model_indexes = _existing_indexes('model_token_usage')
    if 'model_user_model_idx' not in model_indexes:
        op.create_index('model_user_model_idx', 'model_token_usage', ['user_id', 'model_id'], unique=True)
    if 'model_total_idx' not in model_indexes:
        op.create_index('model_total_idx', 'model_token_usage', ['total_tokens'])


def downgrade() -> None:
    tables = _existing_tables()

    for idx_name, table_name in [
        ('model_total_idx', 'model_token_usage'),
        ('model_user_model_idx', 'model_token_usage'),
        ('daily_total_idx', 'daily_token_usage'),
        ('daily_date_idx', 'daily_token_usage'),
        ('daily_user_date_idx', 'daily_token_usage'),
        ('conv_token_total_idx', 'conversation_token_usage'),
        ('conv_token_chat_idx', 'conversation_token_usage'),
        ('conv_token_user_idx', 'conversation_token_usage'),
    ]:
        if idx_name in _existing_indexes(table_name):
            op.drop_index(idx_name, table_name=table_name)

    for table in ('model_token_usage', 'daily_token_usage', 'conversation_token_usage'):
        if table in tables:
            op.drop_table(table)
