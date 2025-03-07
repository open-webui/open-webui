"""
Utility script to check if the city column in the User model is working properly.
This column replaces the model selector functionality in the chat interface.
"""

import logging
import sys
from sqlalchemy import text
from open_webui.internal.db import get_db, engine
from open_webui.models.users import User
from open_webui.env import DATABASE_URL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def check_city_column():
    """Check if the city column exists and is accessible in the User model"""
    log.info("Checking city column in User model...")
    
    # First, check if the table and column exist
    try:
        with engine.connect() as conn:
            # Check if the user table exists
            inspector = conn.dialect.inspector
            tables = inspector.get_table_names()
            if 'user' not in tables:
                log.error("'user' table does not exist in the database!")
                return False
                
            # Check if the city column exists
            columns = [col['name'] for col in inspector.get_columns('user')]
            if 'city' not in columns:
                log.error("'city' column does not exist in the 'user' table!")
                return False
                
            log.info("'city' column exists in 'user' table")
            
            # Check if we can query the city column
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\" WHERE city IS NOT NULL"))
            count = result.scalar()
            log.info(f"Found {count} users with city values")
            
            # Check default value
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\" WHERE city = 'paris'"))
            count = result.scalar()
            log.info(f"Found {count} users with city='paris' (default value)")
            
            return True
            
    except Exception as e:
        log.error(f"Error checking city column: {e}")
        return False
        
def print_connection_info():
    """Print information about the database connection"""
    log.info(f"Database URL: {DATABASE_URL}")
    log.info(f"Engine: {engine.name}")
    log.info(f"Dialect: {engine.dialect.name}")
    
    # Check SSL mode for PostgreSQL
    if engine.dialect.name == 'postgresql':
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SHOW ssl")).scalar()
                log.info(f"PostgreSQL SSL mode: {result}")
        except Exception as e:
            log.error(f"Could not check PostgreSQL SSL mode: {e}")

if __name__ == "__main__":
    log.info("Starting city column check...")
    print_connection_info()
    
    if check_city_column():
        log.info("✅ City column check passed!")
        sys.exit(0)
    else:
        log.error("❌ City column check failed!")
        sys.exit(1) 