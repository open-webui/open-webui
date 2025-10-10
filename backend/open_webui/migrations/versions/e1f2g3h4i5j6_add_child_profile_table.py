"""Add child profile table

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3a4b5c6
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create child_profile table
    op.create_table(
        'child_profile',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('child_age', sa.String(), nullable=True),
        sa.Column('child_gender', sa.String(), nullable=True),
        sa.Column('child_characteristics', sa.Text(), nullable=True),
        sa.Column('parenting_style', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_child_profile_user_id', 'child_profile', ['user_id'])
    op.create_index('idx_child_profile_created_at', 'child_profile', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_child_profile_created_at', table_name='child_profile')
    op.drop_index('idx_child_profile_user_id', table_name='child_profile')
    
    # Drop table
    op.drop_table('child_profile')
