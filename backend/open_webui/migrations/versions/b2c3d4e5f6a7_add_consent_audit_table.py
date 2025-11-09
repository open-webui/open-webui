"""add_consent_audit_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'consent_audit',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('timestamp_utc', sa.BigInteger(), nullable=False),
        sa.Column('consent_version', sa.String(), nullable=True),
        sa.Column('prolific_pid', sa.String(), nullable=True),
        sa.Column('study_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('ui_version', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('consent_given', sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_consent_audit_user', 'consent_audit', ['user_id'])
    op.create_index('idx_consent_audit_timestamp', 'consent_audit', ['timestamp_utc'])
    op.create_index('idx_consent_audit_prolific', 'consent_audit', ['prolific_pid'])
    
    # Drop server default after creation
    with op.batch_alter_table('consent_audit') as batch_op:
        batch_op.alter_column('consent_given', server_default=None)


def downgrade():
    op.drop_index('idx_consent_audit_prolific', table_name='consent_audit')
    op.drop_index('idx_consent_audit_timestamp', table_name='consent_audit')
    op.drop_index('idx_consent_audit_user', table_name='consent_audit')
    op.drop_table('consent_audit')










