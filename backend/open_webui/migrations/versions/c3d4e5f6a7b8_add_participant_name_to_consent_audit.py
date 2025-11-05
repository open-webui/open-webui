"""add_participant_name_to_consent_audit

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Add participant_name column to consent_audit table
    op.add_column('consent_audit', sa.Column('participant_name', sa.String(), nullable=True))


def downgrade():
    # Remove participant_name column
    op.drop_column('consent_audit', 'participant_name')

