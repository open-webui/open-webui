#!/usr/bin/env python3
"""
Reset Usage Data Script
Safely deletes all usage data from SQLite database while preserving configuration data.

Tables to be cleared (usage data):
- client_daily_usage
- client_user_daily_usage 
- client_model_daily_usage
- processed_generations
- processed_generation_cleanup_log

Tables preserved (configuration data):
- client_organizations (organization configs)
- user_client_mapping (user mappings)
- global_settings (system settings)
"""

import sqlite3
import os
import sys
from datetime import datetime
from typing import List, Tuple

# Database path - adjust if needed
DATABASE_PATH = "./data/webui.db"

def get_database_path():
    """Get the database path, checking common locations"""
    possible_paths = [
        "./data/webui.db",
        "../data/webui.db", 
        "./webui.db",
        os.path.expanduser("~/.config/open-webui/webui.db")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    print("❌ Could not find database file. Please specify the correct path.")
    print("Common locations:")
    for path in possible_paths:
        print(f"   - {path}")
    return None

def verify_tables_exist(cursor: sqlite3.Cursor, tables: List[str]) -> Tuple[List[str], List[str]]:
    """Verify which tables exist in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    found_tables = []
    missing_tables = []
    
    for table in tables:
        if table in existing_tables:
            found_tables.append(table)
        else:
            missing_tables.append(table)
    
    return found_tables, missing_tables

def get_table_count(cursor: sqlite3.Cursor, table: str) -> int:
    """Get the number of records in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.Error:
        return 0

def delete_usage_data():
    """Main function to delete usage data"""
    
    # Find database
    db_path = get_database_path()
    if not db_path:
        return False
    
    print(f"📍 Using database: {db_path}")
    
    # Tables to clear (usage data only)
    tables_to_clear = [
        "client_daily_usage",
        "client_user_daily_usage", 
        "client_model_daily_usage",
        "processed_generations",
        "processed_generation_cleanup_log"
    ]
    
    # Tables to preserve (configuration data)
    preserved_tables = [
        "client_organizations",
        "user_client_mapping", 
        "global_settings"
    ]
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Verifying database structure...")
        
        # Check which tables exist
        found_tables, missing_tables = verify_tables_exist(cursor, tables_to_clear)
        
        if missing_tables:
            print(f"⚠️  Warning: Some tables not found: {missing_tables}")
        
        if not found_tables:
            print("❌ No target tables found in database")
            return False
        
        print(f"✅ Found {len(found_tables)} tables to clear: {found_tables}")
        
        # Show current record counts
        print("\\n📊 Current record counts:")
        total_records = 0
        for table in found_tables:
            count = get_table_count(cursor, table)
            print(f"   - {table}: {count:,} records")
            total_records += count
        
        # Show preserved tables
        print("\\n🔒 Configuration tables (will be preserved):")
        for table in preserved_tables:
            count = get_table_count(cursor, table)
            print(f"   - {table}: {count:,} records")
        
        if total_records == 0:
            print("\\n✅ No usage data found to delete.")
            return True
        
        print(f"\\n⚠️  About to delete {total_records:,} usage records from {len(found_tables)} tables.")
        print("Configuration data will be preserved.")
        
        # Confirmation
        response = input("\\nContinue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return False
        
        print("\\n🗑️  Deleting usage data...")
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        deleted_counts = {}
        
        # Delete from each table
        for table in found_tables:
            before_count = get_table_count(cursor, table)
            cursor.execute(f"DELETE FROM {table}")
            after_count = get_table_count(cursor, table)
            deleted_count = before_count - after_count
            deleted_counts[table] = deleted_count
            print(f"   ✅ {table}: {deleted_count:,} records deleted")
        
        # Commit transaction
        cursor.execute("COMMIT")
        
        # Verify deletion
        print("\\n🔍 Verifying deletion...")
        verification_passed = True
        for table in found_tables:
            count = get_table_count(cursor, table)
            if count > 0:
                print(f"   ❌ {table}: {count} records remaining (expected 0)")
                verification_passed = False
            else:
                print(f"   ✅ {table}: 0 records (cleared)")
        
        # Verify preserved tables
        print("\\n🔒 Verifying preserved tables...")
        for table in preserved_tables:
            count = get_table_count(cursor, table)
            print(f"   ✅ {table}: {count:,} records (preserved)")
        
        if verification_passed:
            total_deleted = sum(deleted_counts.values())
            print(f"\\n🎉 SUCCESS: {total_deleted:,} usage records deleted from {len(found_tables)} tables")
            print("✅ Configuration data preserved")
            print("✅ Database ready for new tests")
        else:
            print("\\n❌ VERIFICATION FAILED: Some records may not have been deleted")
            return False
        
        # Optional: Run VACUUM to reclaim space
        response = input("\\nRun VACUUM to reclaim disk space? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            print("🧹 Running VACUUM to reclaim disk space...")
            cursor.execute("VACUUM")
            print("✅ VACUUM completed")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        try:
            cursor.execute("ROLLBACK")
            print("🔄 Transaction rolled back")
        except:
            pass
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🧹 mAI Usage Data Reset Script")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = delete_usage_data()
    
    print()
    print("=" * 50)
    if success:
        print("✅ Usage data reset completed successfully")
        print("🚀 Database is ready for new tests")
    else:
        print("❌ Usage data reset failed")
        print("Please check the errors above and try again")
    
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")