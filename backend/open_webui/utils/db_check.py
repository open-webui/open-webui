"""
Utility script to verify database setup and migrations
"""

import logging
from sqlalchemy import inspect, text
from open_webui.internal.db import engine, get_db
from open_webui.env import DATABASE_URL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def check_database_connection():
    """Verify database connection and configuration"""
    log.info(f"Checking database connection to: {DATABASE_URL}")
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            log.info(f"Database connection test successful: {result}")
            
            # Get database info
            if engine.dialect.name == 'postgresql':
                version = conn.execute(text("SHOW server_version")).scalar()
                log.info(f"PostgreSQL version: {version}")
            elif engine.dialect.name == 'sqlite':
                version = conn.execute(text("SELECT sqlite_version()")).scalar()
                log.info(f"SQLite version: {version}")
                
        return True
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        return False

def check_tables():
    """Check if all required tables exist with correct schema"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        log.info(f"Found tables: {tables}")
        
        # Check user table specifically
        if 'user' in tables:
            columns = {col['name']: col for col in inspector.get_columns('user')}
            log.info("User table columns:")
            for name, details in columns.items():
                log.info(f"  - {name}: {details['type']}")
                
            # Verify city column
            if 'city' in columns:
                log.info("✅ city column exists in user table")
            else:
                log.error("❌ city column missing from user table")
        else:
            log.error("❌ user table not found")
            
        return True
    except Exception as e:
        log.error(f"Error checking tables: {e}")
        return False

def verify_database_setup():
    """Run all database verification checks"""
    log.info("Starting database verification...")
    
    if not check_database_connection():
        return False
        
    if not check_tables():
        return False
        
    log.info("Database verification completed successfully")
    return True

if __name__ == "__main__":
    verify_database_setup() 