"""Add selections table

Revision ID: b1c2d3e4f5a6
Revises: 38d63c18f30f
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = '38d63c18f30f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create selections table
    op.create_table(
        'selection',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('selected_text', sa.Text(), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_selection_user_id', 'selection', ['user_id'])
    op.create_index('idx_selection_chat_id', 'selection', ['chat_id'])
    op.create_index('idx_selection_message_id', 'selection', ['message_id'])
    op.create_index('idx_selection_created_at', 'selection', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_selection_created_at', table_name='selection')
    op.drop_index('idx_selection_message_id', table_name='selection')
    op.drop_index('idx_selection_chat_id', table_name='selection')
    op.drop_index('idx_selection_user_id', table_name='selection')
    
    # Drop table
    op.drop_table('selection')
