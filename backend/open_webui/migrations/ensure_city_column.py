"""
Migration script to ensure the city column exists in the user table.
This column replaces the model selector functionality in the chat interface.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

# Logging configuration
log = logging.getLogger(__name__)

def upgrade():
    """Add city column to the user table if it doesn't exist"""
    try:
        # Check if the column exists before trying to add it
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'city' not in columns:
            log.info("Adding 'city' column to 'user' table")
            op.add_column('user', sa.Column('city', sa.String(), nullable=True, server_default='paris'))
            log.info("'city' column added successfully")
        else:
            log.info("'city' column already exists in 'user' table")
    except Exception as e:
        log.error(f"Error ensuring city column: {e}")
        raise

def downgrade():
    """Remove the city column from the user table"""
    try:
        log.info("Removing 'city' column from 'user' table")
        op.drop_column('user', 'city')
        log.info("'city' column removed successfully")
    except Exception as e:
        log.error(f"Error removing city column: {e}")
        raise 