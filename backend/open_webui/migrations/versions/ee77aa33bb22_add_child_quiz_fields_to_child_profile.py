"""
Add child quiz research fields to child_profile

Revision ID: ee77aa33bb22
Revises: 
Create Date: 2025-10-29 12:50:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ee77aa33bb22'
down_revision = 'ee55ff66aa77'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable columns for backward compatibility
    with op.batch_alter_table('child_profile') as batch_op:
        batch_op.add_column(sa.Column('is_only_child', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('child_has_ai_use', sa.String(), nullable=True))
        # Use JSON if available; fall back to TEXT if driver doesn't support JSON
        try:
            batch_op.add_column(sa.Column('child_ai_use_contexts', sa.JSON(), nullable=True))
        except Exception:
            batch_op.add_column(sa.Column('child_ai_use_contexts', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('parent_llm_monitoring_level', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('child_profile') as batch_op:
        batch_op.drop_column('parent_llm_monitoring_level')
        batch_op.drop_column('child_ai_use_contexts')
        batch_op.drop_column('child_has_ai_use')
        batch_op.drop_column('is_only_child')


