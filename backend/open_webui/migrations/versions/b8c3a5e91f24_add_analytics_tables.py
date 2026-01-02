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


def upgrade() -> None:
    # Create conversation_token_usage table
    # Tracks tokens per chat conversation, updated after each message
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
    
    # Create indexes for conversation_token_usage
    op.create_index('conv_token_user_idx', 'conversation_token_usage', ['user_id'])
    op.create_index('conv_token_chat_idx', 'conversation_token_usage', ['chat_id'], unique=True)
    op.create_index('conv_token_total_idx', 'conversation_token_usage', ['total_tokens'])

    # Create daily_token_usage table
    # Aggregates daily token usage per user for heatmaps
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
    
    # Create indexes for daily_token_usage
    op.create_index('daily_user_date_idx', 'daily_token_usage', ['user_id', 'date'], unique=True)
    op.create_index('daily_date_idx', 'daily_token_usage', ['date'])
    op.create_index('daily_total_idx', 'daily_token_usage', ['total_tokens'])

    # Create model_token_usage table
    # Tracks per-model token usage, supports both per-user and global aggregations
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
    
    # Create indexes for model_token_usage
    op.create_index('model_user_model_idx', 'model_token_usage', ['user_id', 'model_id'], unique=True)
    op.create_index('model_total_idx', 'model_token_usage', ['total_tokens'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('model_total_idx', table_name='model_token_usage')
    op.drop_index('model_user_model_idx', table_name='model_token_usage')
    op.drop_index('daily_total_idx', table_name='daily_token_usage')
    op.drop_index('daily_date_idx', table_name='daily_token_usage')
    op.drop_index('daily_user_date_idx', table_name='daily_token_usage')
    op.drop_index('conv_token_total_idx', table_name='conversation_token_usage')
    op.drop_index('conv_token_chat_idx', table_name='conversation_token_usage')
    op.drop_index('conv_token_user_idx', table_name='conversation_token_usage')
    
    # Drop tables
    op.drop_table('model_token_usage')
    op.drop_table('daily_token_usage')
    op.drop_table('conversation_token_usage')
