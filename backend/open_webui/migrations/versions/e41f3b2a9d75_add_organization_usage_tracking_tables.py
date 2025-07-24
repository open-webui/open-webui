"""Add organization usage tracking tables

Revision ID: e41f3b2a9d75
Revises: d31026856c01
Create Date: 2025-07-24 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "e41f3b2a9d75"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Create organization_settings table
    op.create_table(
        "organization_settings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("openrouter_org_id", sa.String(), nullable=True),
        sa.Column("openrouter_api_key", sa.Text(), nullable=True),
        sa.Column("sync_enabled", sa.Integer(), default=1),
        sa.Column("sync_interval_hours", sa.Integer(), default=1),
        sa.Column("last_sync_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create openrouter_user_mapping table
    op.create_table(
        "openrouter_user_mapping",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owui_user_id", sa.String(), nullable=False),
        sa.Column("openrouter_user_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Integer(), default=1),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create organization_usage table
    op.create_table(
        "organization_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("openrouter_user_id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), default=0),
        sa.Column("output_tokens", sa.BigInteger(), default=0),
        sa.Column("total_tokens", sa.BigInteger(), default=0),
        sa.Column("total_cost", sa.Float(), default=0.0),
        sa.Column("request_count", sa.Integer(), default=0),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("generation_time", sa.Float(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create indexes for performance
    op.create_index("idx_owui_user_id", "openrouter_user_mapping", ["owui_user_id"])
    op.create_index("idx_openrouter_user_id", "openrouter_user_mapping", ["openrouter_user_id"])
    op.create_index("idx_user_date", "organization_usage", ["user_id", "usage_date"])
    op.create_index("idx_model_date", "organization_usage", ["model_name", "usage_date"])
    op.create_index("idx_openrouter_user_date", "organization_usage", ["openrouter_user_id", "usage_date"])


def downgrade():
    # Drop indexes first
    op.drop_index("idx_openrouter_user_date", "organization_usage")
    op.drop_index("idx_model_date", "organization_usage")
    op.drop_index("idx_user_date", "organization_usage")
    op.drop_index("idx_openrouter_user_id", "openrouter_user_mapping")
    op.drop_index("idx_owui_user_id", "openrouter_user_mapping")
    
    # Drop tables
    op.drop_table("organization_usage")
    op.drop_table("openrouter_user_mapping")
    op.drop_table("organization_settings")