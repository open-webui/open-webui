"""Add city column to user table

Revision ID: add_city_column_001
Revises: 3781e22d8b01
Create Date: 2025-03-07 12:12:12.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "add_city_column_001"
down_revision: Union[str, None] = "3781e22d8b01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Check if column exists before adding
        conn = op.get_bind()
        inspector = Inspector.from_engine(conn)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'city' not in columns:
            batch_op.add_column(sa.Column('city', sa.String(), nullable=True, server_default='paris'))

def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('city') 