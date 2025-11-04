"""
Remove parenting_style column from child_profile table

Parenting style is now collected in exit survey instead of child profile creation.
The column is removed from the database schema.

Revision ID: gg11hh22ii33
Revises: fedcba987654
Create Date: 2025-01-03 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'gg11hh22ii33'
down_revision = 'fedcba987654'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove parenting_style column from child_profile table
    with op.batch_alter_table('child_profile') as batch_op:
        batch_op.drop_column('parenting_style')


def downgrade() -> None:
    # Add parenting_style column back for rollback
    with op.batch_alter_table('child_profile') as batch_op:
        batch_op.add_column(sa.Column('parenting_style', sa.String(), nullable=True))

