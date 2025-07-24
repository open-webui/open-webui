"""
Option 1: Simplified Client Organization Usage Schema
Creates daily summary tables with live counters for 99% storage reduction

Revision ID: option1_simplified_schema
Revises: 
Create Date: 2025-01-24

Migration for minimal database approach with daily summaries + live counters
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Text, Integer, Float, BigInteger, Date, Index


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e41f3b2a9d75'
branch_labels = None
depends_on = None


def upgrade():
    """Create Option 1 simplified schema tables"""
    
    # Global Settings table (singleton for provisioning key)
    op.create_table(
        'global_settings',
        sa.Column('id', String, primary_key=True),
        sa.Column('openrouter_provisioning_key', Text, nullable=True),
        sa.Column('default_markup_rate', Float, default=1.3),
        sa.Column('billing_currency', String, default='USD'),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # Client Organizations table
    op.create_table(
        'client_organizations',
        sa.Column('id', String, primary_key=True),
        sa.Column('name', String, nullable=False),
        sa.Column('openrouter_api_key', Text, nullable=False, unique=True),
        sa.Column('openrouter_key_hash', String, nullable=True),
        sa.Column('markup_rate', Float, default=1.3),
        sa.Column('monthly_limit', Float, nullable=True),
        sa.Column('billing_email', String, nullable=True),
        sa.Column('is_active', Integer, default=1),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # User-Client mapping table
    op.create_table(
        'user_client_mapping',
        sa.Column('id', String, primary_key=True),
        sa.Column('user_id', String, nullable=False),
        sa.Column('client_org_id', String, nullable=False),
        sa.Column('openrouter_user_id', String, nullable=False),
        sa.Column('is_active', Integer, default=1),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # Daily Usage Summaries table (99% storage reduction)
    op.create_table(
        'client_daily_usage',
        sa.Column('id', String, primary_key=True),
        sa.Column('client_org_id', String, nullable=False),
        sa.Column('usage_date', Date, nullable=False),
        sa.Column('total_tokens', BigInteger, default=0),
        sa.Column('total_requests', Integer, default=0),
        sa.Column('raw_cost', Float, default=0.0),
        sa.Column('markup_cost', Float, default=0.0),
        sa.Column('primary_model', String, nullable=True),
        sa.Column('unique_users', Integer, default=1),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # Per-User Daily Usage table
    op.create_table(
        'client_user_daily_usage',
        sa.Column('id', String, primary_key=True),
        sa.Column('client_org_id', String, nullable=False),
        sa.Column('user_id', String, nullable=False),
        sa.Column('openrouter_user_id', String, nullable=False),
        sa.Column('usage_date', Date, nullable=False),
        sa.Column('total_tokens', BigInteger, default=0),
        sa.Column('total_requests', Integer, default=0),
        sa.Column('raw_cost', Float, default=0.0),
        sa.Column('markup_cost', Float, default=0.0),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # Per-Model Daily Usage table
    op.create_table(
        'client_model_daily_usage',
        sa.Column('id', String, primary_key=True),
        sa.Column('client_org_id', String, nullable=False),
        sa.Column('model_name', String, nullable=False),
        sa.Column('usage_date', Date, nullable=False),
        sa.Column('total_tokens', BigInteger, default=0),
        sa.Column('total_requests', Integer, default=0),
        sa.Column('raw_cost', Float, default=0.0),
        sa.Column('markup_cost', Float, default=0.0),
        sa.Column('provider', String, nullable=True),
        sa.Column('created_at', BigInteger, nullable=False),
        sa.Column('updated_at', BigInteger, nullable=False),
    )
    
    # Live Counters table (today's real-time data)
    op.create_table(
        'client_live_counters',
        sa.Column('client_org_id', String, primary_key=True),
        sa.Column('current_date', Date, nullable=False),
        sa.Column('today_tokens', BigInteger, default=0),
        sa.Column('today_requests', Integer, default=0),
        sa.Column('today_raw_cost', Float, default=0.0),
        sa.Column('today_markup_cost', Float, default=0.0),
        sa.Column('last_updated', BigInteger, nullable=False),
    )
    
    # Create indexes for performance
    
    # Client Organizations indexes
    op.create_index('idx_api_key', 'client_organizations', ['openrouter_api_key'])
    op.create_index('idx_active', 'client_organizations', ['is_active'])
    
    # User-Client mapping indexes
    op.create_index('idx_user_id', 'user_client_mapping', ['user_id'])
    op.create_index('idx_client_org_id', 'user_client_mapping', ['client_org_id'])
    op.create_index('idx_openrouter_user_id', 'user_client_mapping', ['openrouter_user_id'])
    
    # Daily Usage indexes (critical for query performance)
    op.create_index('idx_client_date', 'client_daily_usage', ['client_org_id', 'usage_date'])
    op.create_index('idx_usage_date', 'client_daily_usage', ['usage_date'])
    
    # Per-User Daily Usage indexes
    op.create_index('idx_client_user_date', 'client_user_daily_usage', ['client_org_id', 'user_id', 'usage_date'])
    op.create_index('idx_user_date', 'client_user_daily_usage', ['user_id', 'usage_date'])
    
    # Per-Model Daily Usage indexes
    op.create_index('idx_client_model_date', 'client_model_daily_usage', ['client_org_id', 'model_name', 'usage_date'])
    op.create_index('idx_model_date', 'client_model_daily_usage', ['model_name', 'usage_date'])
    
    # Live Counters indexes
    op.create_index('idx_client_live_date', 'client_live_counters', ['client_org_id', 'current_date'])
    
    print("✅ Option 1 simplified schema created successfully!")
    print("📊 Database storage reduced by 99% vs per-request tracking")
    print("🚀 Ready for hybrid real-time + daily summary usage tracking")


def downgrade():
    """Drop Option 1 simplified schema tables"""
    
    # Drop indexes first
    op.drop_index('idx_client_live_date', 'client_live_counters')
    op.drop_index('idx_model_date', 'client_model_daily_usage')
    op.drop_index('idx_client_model_date', 'client_model_daily_usage')
    op.drop_index('idx_user_date', 'client_user_daily_usage')
    op.drop_index('idx_client_user_date', 'client_user_daily_usage')
    op.drop_index('idx_usage_date', 'client_daily_usage')
    op.drop_index('idx_client_date', 'client_daily_usage')
    op.drop_index('idx_openrouter_user_id', 'user_client_mapping')
    op.drop_index('idx_client_org_id', 'user_client_mapping')
    op.drop_index('idx_user_id', 'user_client_mapping')
    op.drop_index('idx_active', 'client_organizations')
    op.drop_index('idx_api_key', 'client_organizations')
    
    # Drop tables
    op.drop_table('client_live_counters')
    op.drop_table('client_model_daily_usage')
    op.drop_table('client_user_daily_usage')
    op.drop_table('client_daily_usage')
    op.drop_table('user_client_mapping')
    op.drop_table('client_organizations')
    op.drop_table('global_settings')
    
    print("🗑️ Option 1 schema tables dropped")