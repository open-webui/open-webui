"""
Add child profile other fields

Revision ID: 01e073659718
Revises: m67n78o89p90
Create Date: 2025-01-22 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "01e073659718"
down_revision = "m67n78o89p90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable columns for "Other" text fields to child_profile table
    # These columns store additional text when users select "Other" option
    # Make migration idempotent by checking if columns exist before adding them
    
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Get existing columns in the child_profile table
    existing_columns = [col["name"] for col in inspector.get_columns("child_profile")]
    
    with op.batch_alter_table("child_profile") as batch_op:
        # Only add columns that don't already exist
        if "child_gender_other" not in existing_columns:
            batch_op.add_column(sa.Column("child_gender_other", sa.Text(), nullable=True))
        
        if "child_ai_use_contexts_other" not in existing_columns:
            batch_op.add_column(sa.Column("child_ai_use_contexts_other", sa.Text(), nullable=True))
        
        if "parent_llm_monitoring_other" not in existing_columns:
            batch_op.add_column(sa.Column("parent_llm_monitoring_other", sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove the "Other" text fields columns
    with op.batch_alter_table("child_profile") as batch_op:
        batch_op.drop_column("parent_llm_monitoring_other")
        batch_op.drop_column("child_ai_use_contexts_other")
        batch_op.drop_column("child_gender_other")

