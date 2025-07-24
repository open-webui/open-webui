"""Merge heads: main branch and option1 schema

Revision ID: merge_heads_option1
Revises: d31026856c01, f1a2b3c4d5e6
Create Date: 2025-07-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_option1'
down_revision = ('d31026856c01', 'f1a2b3c4d5e6')
branch_labels = None
depends_on = None

def upgrade():
    """Merge migration - no changes needed"""
    pass

def downgrade():
    """Merge migration - no changes needed"""
    pass