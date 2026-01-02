"""
Add attention check tables

Revision ID: ee88bb99cc11
Revises: ee77aa33bb22
Create Date: 2025-10-29 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'ee88bb99cc11'
down_revision = 'ee77aa33bb22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # attention_check_question table
    if "attention_check_question" not in existing_tables:
        op.create_table(
            'attention_check_question',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('prompt', sa.String(), nullable=False),
            sa.Column('options', sa.String(), nullable=False),
            sa.Column('correct_option', sa.String(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_acq_created_at', 'attention_check_question', ['created_at'])
    else:
        # Table exists, check if index exists
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("attention_check_question")]
        if "idx_acq_created_at" not in existing_indexes:
            op.create_index('idx_acq_created_at', 'attention_check_question', ['created_at'])
    
    # attention_check_response table
    if "attention_check_response" not in existing_tables:
        op.create_table(
            'attention_check_response',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('session_number', sa.Integer(), nullable=True),
            sa.Column('question_id', sa.String(), nullable=False),
            sa.Column('response', sa.String(), nullable=False),
            sa.Column('is_passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_acr_user', 'attention_check_response', ['user_id'])
        op.create_index('idx_acr_question', 'attention_check_response', ['question_id'])
        op.create_index('idx_acr_created_at', 'attention_check_response', ['created_at'])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("attention_check_response")]
        indexes_to_create = [
            ('idx_acr_user', ['user_id']),
            ('idx_acr_question', ['question_id']),
            ('idx_acr_created_at', ['created_at']),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, 'attention_check_response', columns)


def downgrade() -> None:
    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "attention_check_response" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("attention_check_response")]
        indexes_to_drop = [
            'idx_acr_created_at',
            'idx_acr_question',
            'idx_acr_user',
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name='attention_check_response')
        op.drop_table('attention_check_response')
    
    if "attention_check_question" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("attention_check_question")]
        if "idx_acq_created_at" in existing_indexes:
            op.drop_index('idx_acq_created_at', table_name='attention_check_question')
        op.drop_table('attention_check_question')
