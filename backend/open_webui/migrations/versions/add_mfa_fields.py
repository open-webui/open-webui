"""Add MFA related fields to Auth and User Models

Revision ID: add_mfa_fields
Revises: 3781e22d8b01
Create Date: 2025-03-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_mfa_fields'
down_revision = '3781e22d8b01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth', sa.Column('mfa_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('auth', sa.Column('mfa_secret', sa.Text(), nullable=True))
    op.add_column('auth', sa.Column('backup_codes', sa.Text(), nullable=True))  
    op.add_column('auth', sa.Column('mfa_last_used', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('mfa_enabled', sa.Boolean(), nullable=True, server_default='false'))

def downgrade():
    op.drop_column('auth', 'mfa_enabled')
    op.drop_column('auth', 'mfa_secret')
    op.drop_column('auth', 'backup_codes')
    op.drop_column('auth', 'mfa_last_used')
    op.drop_column('user', 'mfa_enabled')

