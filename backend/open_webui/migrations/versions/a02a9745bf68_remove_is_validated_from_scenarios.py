"""remove_is_validated_from_scenarios

Revision ID: a02a9745bf68
Revises: p00q11r22s33
Create Date: 2026-01-09 19:46:15.062548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'a02a9745bf68'
down_revision: Union[str, None] = 'p00q11r22s33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "scenarios" in existing_tables:
        # Check if index exists before dropping
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('scenarios')]
        if 'idx_scenarios_is_validated' in existing_indexes:
            op.drop_index('idx_scenarios_is_validated', table_name='scenarios')
        
        # Check if column exists before dropping
        existing_columns = [col['name'] for col in inspector.get_columns('scenarios')]
        if 'is_validated' in existing_columns:
            op.drop_column('scenarios', 'is_validated')


def downgrade() -> None:
    # Re-add the column and index if they don't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "scenarios" in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('scenarios')]
        if 'is_validated' not in existing_columns:
            op.add_column('scenarios', sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='0'))
        
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('scenarios')]
        if 'idx_scenarios_is_validated' not in existing_indexes:
            op.create_index('idx_scenarios_is_validated', 'scenarios', ['is_validated'])
