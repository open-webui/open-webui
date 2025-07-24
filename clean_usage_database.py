#!/usr/bin/env python3
"""
Clean Usage Database Script for mAI
Safely clears all usage data while preserving configuration and user data
"""

import sqlite3
import time
from datetime import date
import os

DB_PATH = "backend/open_webui/data/webui.db"

def backup_database():
    """Create a backup of the current database"""
    backup_path = f"backend/open_webui/data/webui_backup_{int(time.time())}.db"
    
    if os.path.exists(DB_PATH):
        try:
            # Create backup using SQLite backup API
            source = sqlite3.connect(DB_PATH)
            backup = sqlite3.connect(backup_path)
            source.backup(backup)
            source.close()
            backup.close()
            print(f"✅ Database backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    else:
        print("ℹ️  No existing database to backup")
        return None

def clear_usage_data():
    """Safely clear all usage-related data while preserving configuration"""
    
    if not os.path.exists(DB_PATH):
        print("ℹ️  Database file doesn't exist - nothing to clear")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("🧹 Starting usage data cleanup...")
        
        # 1. Clear live counters (today's usage)
        cursor.execute("DELETE FROM client_live_counters")
        deleted_live = cursor.rowcount
        print(f"   Cleared {deleted_live} live counter records")
        
        # 2. Clear daily usage summaries
        cursor.execute("DELETE FROM client_daily_usage")
        deleted_daily = cursor.rowcount
        print(f"   Cleared {deleted_daily} daily usage records")
        
        # 3. Clear per-user daily usage
        cursor.execute("DELETE FROM client_user_daily_usage")
        deleted_user = cursor.rowcount
        print(f"   Cleared {deleted_user} user daily usage records")
        
        # 4. Clear per-model daily usage
        cursor.execute("DELETE FROM client_model_daily_usage")
        deleted_model = cursor.rowcount
        print(f"   Cleared {deleted_model} model daily usage records")
        
        # Reset auto-increment sequences (if any)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('client_live_counters', 'client_daily_usage', 'client_user_daily_usage', 'client_model_daily_usage')")
        
        conn.commit()
        
        # 5. Verify tables are empty
        print("\n📊 Verification:")
        tables_to_check = [
            "client_live_counters",
            "client_daily_usage", 
            "client_user_daily_usage",
            "client_model_daily_usage"
        ]
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                status = "✅ Empty" if count == 0 else f"⚠️  Still has {count} records"
                print(f"   {table}: {status}")
            except sqlite3.OperationalError:
                print(f"   {table}: ℹ️  Table doesn't exist")
        
        # 6. Show preserved data
        print("\n🔒 Preserved configuration data:")
        preserved_tables = [
            ("client_organizations", "Client organizations and API keys"),
            ("user_client_mapping", "User-to-organization mappings"),
            ("global_settings", "System configuration")
        ]
        
        for table, description in preserved_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count} records - {description}")
            except sqlite3.OperationalError:
                print(f"   {table}: ℹ️  Table doesn't exist - {description}")
        
        total_cleared = deleted_live + deleted_daily + deleted_user + deleted_model
        print(f"\n✅ Successfully cleared {total_cleared} usage records")
        print("   All billing data reset to zero")
        print("   Ready for fresh usage tracking")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

def reset_usage_counters_to_zero():
    """Ensure all counters start from zero for clean measurement"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        current_time = int(time.time())
        today = date.today()
        
        print("\n🔄 Initializing clean usage tracking...")
        
        # Get all active client organizations
        cursor.execute("SELECT id, name FROM client_organizations WHERE is_active = 1")
        clients = cursor.fetchall()
        
        if clients:
            print(f"   Found {len(clients)} active client organizations")
            
            # Initialize clean live counters for each client
            for client_id, client_name in clients:
                cursor.execute("""
                    INSERT OR REPLACE INTO client_live_counters 
                    (client_org_id, current_date, today_tokens, today_requests, 
                     today_raw_cost, today_markup_cost, last_updated)
                    VALUES (?, ?, 0, 0, 0.0, 0.0, ?)
                """, (client_id, today, current_time))
                
                print(f"   ✅ Initialized clean counters for: {client_name}")
            
            conn.commit()
            print("   🎯 All clients ready for fresh usage measurement")
        else:
            print("   ℹ️  No active client organizations found")
            print("   💡 You may need to create client organizations first")
        
    except Exception as e:
        print(f"❌ Error initializing counters: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main cleanup process"""
    print("🧹 mAI Usage Database Cleanup Tool")
    print("=" * 50)
    
    # Step 1: Create backup
    backup_path = backup_database()
    
    # Step 2: Confirm cleanup
    print("\n⚠️  This will clear ALL usage data including:")
    print("   - Today's live counters")
    print("   - Historical daily usage")
    print("   - Per-user usage history") 
    print("   - Per-model usage history")
    print("\n✅ This will PRESERVE:")
    print("   - Client organizations and API keys")
    print("   - User mappings")
    print("   - System settings")
    print("   - All other Open WebUI data")
    
    if backup_path:
        print(f"\n💾 Backup created: {backup_path}")
    
    response = input("\n❓ Continue with cleanup? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        # Step 3: Clear usage data
        clear_usage_data()
        
        # Step 4: Initialize clean counters
        reset_usage_counters_to_zero()
        
        print("\n🎉 Database cleanup completed!")
        print("   📊 Usage tracking reset to zero")
        print("   🚀 Ready for fresh usage measurement")
        
        if backup_path:
            print(f"   💾 Backup available at: {backup_path}")
            
    else:
        print("❌ Cleanup cancelled by user")

if __name__ == "__main__":
    main()