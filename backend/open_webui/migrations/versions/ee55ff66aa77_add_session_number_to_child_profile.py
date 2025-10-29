"""add session_number to child_profile

Revision ID: ee55ff66aa77
Revises: dd44ee55ff66
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee55ff66aa77'
down_revision = 'dd44ee55ff66'
branch_labels = None
depends_on = None


def upgrade():
    # Add session_number to child_profile
    op.add_column('child_profile', sa.Column('session_number', sa.BigInteger(), nullable=False, server_default='1'))

    # Add index for lookups
    op.create_index('idx_child_profile_user_session_current', 'child_profile', ['user_id', 'session_number', 'is_current'])


def downgrade():
    op.drop_index('idx_child_profile_user_session_current', table_name='child_profile')
    op.drop_column('child_profile', 'session_number')


