"""Add encryption fields to user table

Revision ID: c4a3b2d1e0f
Revises: 9f0c9cd09105
Create Date: 2025-07-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a3b2d1e0f'
down_revision = '9f0c9cd09105' # The last stable migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Add all new fields with the correct LargeBinary type
        batch_op.add_column(sa.Column('salt', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('user_encrypted_dek', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('user_key', sa.LargeBinary(), nullable=True)) # Temporary field
        batch_op.add_column(sa.Column('kms_encrypted_dek', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    # This function correctly reverses the changes
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('kms_encrypted_dek')
        batch_op.drop_column('user_key')
        batch_op.drop_column('user_encrypted_dek')
        batch_op.drop_column('salt')
