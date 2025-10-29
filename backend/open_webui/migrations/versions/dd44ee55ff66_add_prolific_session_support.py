"""add_prolific_session_support

Revision ID: dd44ee55ff66
Revises: cc33dd44ee55
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd44ee55ff66'
down_revision = 'cc33dd44ee55'
branch_labels = None
depends_on = None


def upgrade():
    # Add Prolific fields to user table
    op.add_column('user', sa.Column('prolific_pid', sa.String(), nullable=True))
    op.add_column('user', sa.Column('study_id', sa.String(), nullable=True))
    op.add_column('user', sa.Column('current_session_id', sa.String(), nullable=True))
    op.add_column('user', sa.Column('session_number', sa.BigInteger(), nullable=False, server_default='1'))
    
    # Add unique constraint for prolific_pid
    op.create_unique_constraint('uq_user_prolific_pid', 'user', ['prolific_pid'])
    
    # Add session_number to moderation_session table
    op.add_column('moderation_session', sa.Column('session_number', sa.BigInteger(), nullable=False, server_default='1'))
    
    # Update composite index to include session_number
    op.drop_index('idx_mod_session_composite', table_name='moderation_session')
    op.create_index('idx_mod_session_composite', 'moderation_session', ['user_id', 'child_id', 'scenario_index', 'attempt_number', 'session_number'])
    
    # Add new index for user session queries
    op.create_index('idx_mod_session_user_session', 'moderation_session', ['user_id', 'session_number'])


def downgrade():
    # Remove new indexes
    op.drop_index('idx_mod_session_user_session', table_name='moderation_session')
    op.drop_index('idx_mod_session_composite', table_name='moderation_session')
    
    # Restore original composite index
    op.create_index('idx_mod_session_composite', 'moderation_session', ['user_id', 'child_id', 'scenario_index', 'attempt_number'])
    
    # Remove session_number from moderation_session
    op.drop_column('moderation_session', 'session_number')
    
    # Remove Prolific fields from user table
    op.drop_constraint('uq_user_prolific_pid', 'user', type_='unique')
    op.drop_column('user', 'session_number')
    op.drop_column('user', 'current_session_id')
    op.drop_column('user', 'study_id')
    op.drop_column('user', 'prolific_pid')
