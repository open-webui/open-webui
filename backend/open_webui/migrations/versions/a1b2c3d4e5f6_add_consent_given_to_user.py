"""add_consent_given_to_user

Revision ID: a1b2c3d4e5f6
Revises: fedcba987654
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fedcba987654'
branch_labels = None
depends_on = None


def upgrade():
    # Add consent_given column to user table
    op.add_column('user', sa.Column('consent_given', sa.Boolean(), nullable=True, server_default=sa.sql.expression.false()))
    
    # Drop server default after adding column (to allow NULL for not yet asked)
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('consent_given', server_default=None)


def downgrade():
    # Remove consent_given column
    op.drop_column('user', 'consent_given')

