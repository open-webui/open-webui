#!/usr/bin/env python3
"""
Database Migration Script: Add timezone field to client_organizations table

This script adds the timezone field to existing client organizations 
and sets the default to "Europe/Warsaw" for Polish clients.
"""

import sqlite3
import os
import sys
from datetime import datetime

# Database path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "..", "data")  # Adjust as needed
DB_PATH = os.path.join(DATA_DIR, "webui.db")

def check_database_exists():
    """Check if the database file exists"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Please check your database path configuration")
        return False
    
    print(f"✅ Database found at: {DB_PATH}")
    return True

def check_table_exists(cursor):
    """Check if client_organizations table exists"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='client_organizations'
    """)
    
    exists = cursor.fetchone() is not None
    if exists:
        print("✅ client_organizations table exists")
    else:
        print("❌ client_organizations table not found")
    
    return exists

def check_timezone_field_exists(cursor):
    """Check if timezone field already exists"""
    cursor.execute("PRAGMA table_info(client_organizations)")
    columns = cursor.fetchall()
    
    timezone_exists = any(col[1] == 'timezone' for col in columns)
    
    if timezone_exists:
        print("✅ timezone field already exists")
    else:
        print("❌ timezone field needs to be added")
    
    return timezone_exists

def add_timezone_field(cursor):
    """Add timezone field to client_organizations table"""
    try:
        cursor.execute("""
            ALTER TABLE client_organizations 
            ADD COLUMN timezone TEXT DEFAULT 'Europe/Warsaw'
        """)
        print("✅ Added timezone field to client_organizations table")
        return True
    except sqlite3.Error as e:
        print(f"❌ Failed to add timezone field: {e}")
        return False

def update_existing_clients_timezone(cursor):
    """Update existing clients to have Poland timezone"""
    try:
        # Count existing clients
        cursor.execute("SELECT COUNT(*) FROM client_organizations")
        client_count = cursor.fetchone()[0]
        
        if client_count == 0:
            print("ℹ️  No existing clients found - nothing to update")
            return True
        
        # Update all existing clients to Poland timezone
        cursor.execute("""
            UPDATE client_organizations 
            SET timezone = 'Europe/Warsaw' 
            WHERE timezone IS NULL OR timezone = ''
        """)
        
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} existing clients to Poland timezone")
        
        # Verify the update
        cursor.execute("""
            SELECT name, timezone FROM client_organizations 
            ORDER BY created_at DESC LIMIT 5
        """)
        
        recent_clients = cursor.fetchall()
        if recent_clients:
            print("   Recent clients with timezone:")
            for name, timezone in recent_clients:
                print(f"     - {name}: {timezone}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Failed to update existing clients: {e}")
        return False

def create_backup():
    """Create a backup of the database before migration"""
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Database backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Failed to create backup: {e}")
        return None

def verify_migration(cursor):
    """Verify the migration was successful"""
    try:
        # Check that timezone field exists and has correct default
        cursor.execute("PRAGMA table_info(client_organizations)")
        columns = cursor.fetchall()
        
        timezone_column = None
        for col in columns:
            if col[1] == 'timezone':
                timezone_column = col
                break
        
        if not timezone_column:
            print("❌ Verification failed: timezone field not found")
            return False
        
        # Check default value
        default_value = timezone_column[4]  # Default value is at index 4
        if default_value != "'Europe/Warsaw'":
            print(f"⚠️  Default value is '{default_value}', expected 'Europe/Warsaw'")
        else:
            print("✅ Default timezone value is correct")
        
        # Check existing data
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN timezone = 'Europe/Warsaw' THEN 1 END) as poland_tz,
                   COUNT(CASE WHEN timezone IS NULL OR timezone = '' THEN 1 END) as null_tz
            FROM client_organizations
        """)
        
        total, poland_tz, null_tz = cursor.fetchone()
        
        print(f"✅ Migration verification:")
        print(f"     Total clients: {total}")
        print(f"     Poland timezone: {poland_tz}")
        print(f"     Null/empty timezone: {null_tz}")
        
        return null_tz == 0  # All should have timezone set
        
    except sqlite3.Error as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Run the timezone field migration"""
    print("=" * 60)
    print("Database Migration: Add timezone field for Polish clients")
    print("=" * 60)
    
    # Check database exists
    if not check_database_exists():
        return 1
    
    # Create backup
    backup_path = create_backup()
    if not backup_path:
        response = input("⚠️  Continue without backup? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return 1
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n🔍 Checking current database state...")
        
        # Check table exists
        if not check_table_exists(cursor):
            print("Cannot proceed without client_organizations table")
            return 1
        
        # Check if migration is needed
        if check_timezone_field_exists(cursor):
            print("✅ Timezone field already exists - checking data consistency...")
            
            # Still verify and update existing data if needed
            if not update_existing_clients_timezone(cursor):
                return 1
        else:
            print("\n🔧 Adding timezone field...")
            
            # Add the timezone field
            if not add_timezone_field(cursor):
                return 1
            
            # Update existing clients
            if not update_existing_clients_timezone(cursor):
                return 1
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration changes committed to database")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        if verify_migration(cursor):
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Migration completed but verification found issues")
        
        conn.close()
        
        print(f"\n🇵🇱 All clients now configured for Polish timezone (Europe/Warsaw)")
        print(f"   Database backup: {backup_path if backup_path else 'None created'}")
        
        return 0
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if 'conn' in locals():
            conn.close()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)