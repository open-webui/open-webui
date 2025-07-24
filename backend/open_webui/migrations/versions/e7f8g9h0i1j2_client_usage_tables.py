"""Add client organization usage tracking tables

Revision ID: e7f8g9h0i1j2
Revises: d31026856c01
Create Date: 2025-07-24 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'd31026856c01'
branch_labels = None
depends_on = None

def upgrade():
    """Create client organization usage tracking tables"""
    
    # Global Settings table
    op.create_table('global_settings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('openrouter_provisioning_key', sa.Text(), nullable=True),
        sa.Column('default_markup_rate', sa.Float(), nullable=True, default=1.3),
        sa.Column('billing_currency', sa.String(), nullable=True, default='USD'),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Client Organizations table
    op.create_table('client_organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('openrouter_api_key', sa.Text(), nullable=False),
        sa.Column('openrouter_key_hash', sa.String(), nullable=True),
        sa.Column('markup_rate', sa.Float(), nullable=True, default=1.3),
        sa.Column('monthly_limit', sa.Float(), nullable=True),
        sa.Column('billing_email', sa.String(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('openrouter_api_key')
    )
    
    # User-Client mapping table
    op.create_table('user_client_mapping',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('client_org_id', sa.String(), nullable=False),
        sa.Column('openrouter_user_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Daily Usage Summaries table
    op.create_table('client_daily_usage',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('client_org_id', sa.String(), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
        sa.Column('total_requests', sa.Integer(), nullable=True, default=0),
        sa.Column('raw_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('markup_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('primary_model', sa.String(), nullable=True),
        sa.Column('unique_users', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Per-User Daily Usage table
    op.create_table('client_user_daily_usage',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('client_org_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('openrouter_user_id', sa.String(), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
        sa.Column('total_requests', sa.Integer(), nullable=True, default=0),
        sa.Column('raw_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('markup_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Per-Model Daily Usage table
    op.create_table('client_model_daily_usage',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('client_org_id', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('total_tokens', sa.BigInteger(), nullable=True, default=0),
        sa.Column('total_requests', sa.Integer(), nullable=True, default=0),
        sa.Column('raw_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('markup_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Live Counters table
    op.create_table('client_live_counters',
        sa.Column('client_org_id', sa.String(), nullable=False),
        sa.Column('current_date', sa.Date(), nullable=False),
        sa.Column('today_tokens', sa.BigInteger(), nullable=True, default=0),
        sa.Column('today_requests', sa.Integer(), nullable=True, default=0),
        sa.Column('today_raw_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('today_markup_cost', sa.Float(), nullable=True, default=0.0),
        sa.Column('last_updated', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('client_org_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_api_key', 'client_organizations', ['openrouter_api_key'])
    op.create_index('idx_active', 'client_organizations', ['is_active'])
    op.create_index('idx_user_id', 'user_client_mapping', ['user_id'])
    op.create_index('idx_client_org_id', 'user_client_mapping', ['client_org_id'])
    op.create_index('idx_openrouter_user_id', 'user_client_mapping', ['openrouter_user_id'])
    op.create_index('idx_client_date', 'client_daily_usage', ['client_org_id', 'usage_date'])
    op.create_index('idx_usage_date', 'client_daily_usage', ['usage_date'])
    op.create_index('idx_client_user_date', 'client_user_daily_usage', ['client_org_id', 'user_id', 'usage_date'])
    op.create_index('idx_user_date', 'client_user_daily_usage', ['user_id', 'usage_date'])
    op.create_index('idx_client_model_date', 'client_model_daily_usage', ['client_org_id', 'model_name', 'usage_date'])
    op.create_index('idx_model_date', 'client_model_daily_usage', ['model_name', 'usage_date'])
    op.create_index('idx_client_live_date', 'client_live_counters', ['client_org_id', 'current_date'])

def downgrade():
    """Drop client organization usage tracking tables"""
    
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