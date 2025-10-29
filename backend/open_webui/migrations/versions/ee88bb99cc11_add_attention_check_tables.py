"""
Add attention check tables

Revision ID: ee88bb99cc11
Revises: ee77aa33bb22
Create Date: 2025-10-29 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ee88bb99cc11'
down_revision = 'ee77aa33bb22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'attention_check_question',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('prompt', sa.String(), nullable=False),
        sa.Column('options', sa.String(), nullable=False),
        sa.Column('correct_option', sa.String(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('idx_acq_created_at', 'attention_check_question', ['created_at'])

    op.create_table(
        'attention_check_response',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_number', sa.Integer(), nullable=True),
        sa.Column('question_id', sa.String(), nullable=False),
        sa.Column('response', sa.String(), nullable=False),
        sa.Column('is_passed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('idx_acr_user', 'attention_check_response', ['user_id'])
    op.create_index('idx_acr_question', 'attention_check_response', ['question_id'])
    op.create_index('idx_acr_created_at', 'attention_check_response', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_acr_created_at', table_name='attention_check_response')
    op.drop_index('idx_acr_question', table_name='attention_check_response')
    op.drop_index('idx_acr_user', table_name='attention_check_response')
    op.drop_table('attention_check_response')
    op.drop_index('idx_acq_created_at', table_name='attention_check_question')
    op.drop_table('attention_check_question')


