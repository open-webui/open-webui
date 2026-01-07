"""Update selection table to add assignment_id and offset fields

Revision ID: o00p11q22r33
Revises: n99o00p11q22
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'o00p11q22r33'
down_revision = 'n99o00p11q22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    if "selection" in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('selection')]
        
        # Add assignment_id if it doesn't exist
        if 'assignment_id' not in columns:
            with op.batch_alter_table('selection') as batch_op:
                batch_op.add_column(sa.Column('assignment_id', sa.String(), nullable=True))
            op.create_index('idx_selection_assignment_id', 'selection', ['assignment_id'])
            # Note: Foreign key constraint not created for SQLite compatibility
            # SQLite doesn't support ALTER TABLE ADD CONSTRAINT
            # Foreign key relationship is enforced at application level
        
        # Add start_offset if it doesn't exist
        if 'start_offset' not in columns:
            op.add_column('selection', sa.Column('start_offset', sa.Integer(), nullable=True))
        
        # Add end_offset if it doesn't exist
        if 'end_offset' not in columns:
            op.add_column('selection', sa.Column('end_offset', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    if "selection" in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('selection')]
        
        if 'end_offset' in columns:
            op.drop_column('selection', 'end_offset')
        
        if 'start_offset' in columns:
            op.drop_column('selection', 'start_offset')
        
        if 'assignment_id' in columns:
            op.drop_index('idx_selection_assignment_id', table_name='selection')
            with op.batch_alter_table('selection') as batch_op:
                batch_op.drop_column('assignment_id')

