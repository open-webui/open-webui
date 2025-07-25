#!/usr/bin/env python3
"""
Fix database schema by adding missing timezone column
"""

import sqlite3
import sys

def fix_database_schema():
    """Add missing timezone column to client_organizations table"""
    print("🔧 FIXING: Database Schema")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = sqlite3.connect('/app/backend/data/webui.db')
        cursor = conn.cursor()
        
        # Check if timezone column exists
        cursor.execute("PRAGMA table_info(client_organizations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📊 Current columns: {column_names}")
        
        if 'timezone' not in column_names:
            print("⚠️ Missing timezone column, adding it...")
            
            # Add timezone column with default value
            cursor.execute("""
                ALTER TABLE client_organizations 
                ADD COLUMN timezone VARCHAR DEFAULT 'Europe/Warsaw'
            """)
            
            conn.commit()
            print("✅ Added timezone column")
            
            # Verify the addition
            cursor.execute("PRAGMA table_info(client_organizations)")
            new_columns = cursor.fetchall()
            new_column_names = [col[1] for col in new_columns]
            
            print(f"📊 New columns: {new_column_names}")
            
            if 'timezone' in new_column_names:
                print("✅ Schema fix successful!")
                return True
            else:
                print("❌ Schema fix failed!")
                return False
        else:
            print("✅ timezone column already exists")
            return True
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n🎯 Database schema is now compatible!")
        print("The sync function should work correctly now.")
    else:
        print("\n❌ Schema fix failed!")
        sys.exit(1)