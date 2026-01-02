"""add session_number to child_profile

Revision ID: ee55ff66aa77
Revises: dd44ee55ff66
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'ee55ff66aa77'
down_revision = 'dd44ee55ff66'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "child_profile" in existing_tables:
        child_profile_columns = [col["name"] for col in inspector.get_columns("child_profile")]
        if "session_number" not in child_profile_columns:
            # Add session_number to child_profile
            op.add_column('child_profile', sa.Column('session_number', sa.BigInteger(), nullable=False, server_default='1'))
        
        # Check if index exists
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("child_profile")]
        if "idx_child_profile_user_session_current" not in existing_indexes:
            # Add index for lookups
            op.create_index('idx_child_profile_user_session_current', 'child_profile', ['user_id', 'session_number', 'is_current'])


def downgrade():
    # Check if column/index exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "child_profile" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("child_profile")]
        if "idx_child_profile_user_session_current" in existing_indexes:
            op.drop_index('idx_child_profile_user_session_current', table_name='child_profile')
        child_profile_columns = [col["name"] for col in inspector.get_columns("child_profile")]
        if "session_number" in child_profile_columns:
            op.drop_column('child_profile', 'session_number')
