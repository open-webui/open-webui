#!/usr/bin/env python3
"""
Fix missing processed_generation_cleanup_log table in existing databases.
This table is used for tracking cleanup operations but isn't always created.
"""

import sqlite3
import os
import sys
from pathlib import Path

def find_database():
    """Find the database file."""
    # Check multiple possible locations
    possible_paths = [
        "backend/data/webui.db",
        "data/webui.db",
        "../data/webui.db",
        "../../backend/data/webui.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    # If not found, construct the expected path
    script_dir = Path(__file__).parent
    db_path = script_dir.parent / "data" / "webui.db"
    if db_path.exists():
        return str(db_path)
    
    return None

def create_missing_table(db_path):
    """Create the processed_generation_cleanup_log table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='processed_generation_cleanup_log'
        """)
        
        if cursor.fetchone():
            print("✅ Table 'processed_generation_cleanup_log' already exists")
            return True
        
        print("⚠️  Table 'processed_generation_cleanup_log' is missing")
        print("ℹ️  Creating the table...")
        
        # Create the table with all required columns and indexes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_generation_cleanup_log (
                generation_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'cleaned',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cleanup_log_org_id 
            ON processed_generation_cleanup_log(organization_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cleanup_log_processed_at 
            ON processed_generation_cleanup_log(processed_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cleanup_log_status 
            ON processed_generation_cleanup_log(status)
        """)
        
        conn.commit()
        
        # Verify creation
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='processed_generation_cleanup_log'
        """)
        
        if cursor.fetchone():
            print("✅ Successfully created 'processed_generation_cleanup_log' table")
            print("✅ Created indexes for optimal performance")
            return True
        else:
            print("❌ Failed to create table")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """Main function."""
    print("🔧 Fixing Missing processed_generation_cleanup_log Table")
    print("=" * 60)
    
    # Find database
    db_path = find_database()
    if not db_path:
        print("❌ Could not find database file (webui.db)")
        print("ℹ️  Please run this script from the mAI project root directory")
        sys.exit(1)
    
    print(f"📁 Found database: {db_path}")
    
    # Create the missing table
    if create_missing_table(db_path):
        print("\n✅ Database fix completed successfully!")
        print("ℹ️  You can now run generate_client_env without issues")
    else:
        print("\n❌ Failed to fix database")
        sys.exit(1)

if __name__ == "__main__":
    main()