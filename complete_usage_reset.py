#!/usr/bin/env python3
"""
Complete Usage System Reset for mAI
Clears ALL usage-related data including organizations and mappings
Use this for complete fresh start
"""

import sqlite3
import time
import os

DB_PATH = "backend/open_webui/data/webui.db"

def complete_usage_reset():
    """Complete reset of all usage-related tables and data"""
    
    if not os.path.exists(DB_PATH):
        print("ℹ️  Database file doesn't exist - nothing to reset")
        return
        
    # Create backup first
    backup_path = f"backend/open_webui/data/webui_complete_backup_{int(time.time())}.db"
    source = sqlite3.connect(DB_PATH)
    backup = sqlite3.connect(backup_path)
    source.backup(backup)
    source.close()
    backup.close()
    print(f"✅ Complete backup created: {backup_path}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("🔥 Starting COMPLETE usage system reset...")
        
        # Clear all usage tables in correct order (respecting foreign keys)
        tables_to_clear = [
            ("client_live_counters", "Live usage counters"),
            ("client_daily_usage", "Daily usage summaries"),
            ("client_user_daily_usage", "Per-user daily usage"),
            ("client_model_daily_usage", "Per-model daily usage"),
            ("user_client_mapping", "User-organization mappings"),
            ("client_organizations", "Client organizations and API keys"),
            ("global_settings", "Usage system settings")
        ]
        
        total_cleared = 0
        
        for table_name, description in tables_to_clear:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                cursor.execute(f"DELETE FROM {table_name}")
                deleted = cursor.rowcount
                total_cleared += deleted
                
                print(f"   ✅ {table_name}: Cleared {deleted} records - {description}")
            except sqlite3.OperationalError as e:
                print(f"   ℹ️  {table_name}: Table doesn't exist - {description}")
        
        # Reset sequences
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('client_organizations', 'user_client_mapping', 'client_live_counters', 'client_daily_usage', 'client_user_daily_usage', 'client_model_daily_usage', 'global_settings')")
        
        conn.commit()
        
        print(f"\n🔥 COMPLETE RESET FINISHED")
        print(f"   📊 Total records cleared: {total_cleared}")
        print(f"   💾 Backup saved: {backup_path}")
        print("\n⚠️  You will need to:")
        print("   1. Reconfigure client organizations")
        print("   2. Set up user mappings")
        print("   3. Configure OpenRouter API keys")
        print("   4. Restart the application")
        
    except Exception as e:
        print(f"❌ Error during complete reset: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    print("🔥 mAI COMPLETE Usage System Reset")
    print("=" * 50)
    print("⚠️  DANGER: This will completely remove:")
    print("   🗑️  All client organizations")
    print("   🗑️  All user mappings") 
    print("   🗑️  All usage data and history")
    print("   🗑️  All usage system configuration")
    print("\n✅ This will PRESERVE:")
    print("   💾 All other Open WebUI data (chats, users, models, etc.)")
    print("   💾 Complete backup will be created")
    
    print("\n❓ This is for starting completely fresh with usage tracking.")
    print("❓ If you only want to clear usage data, use clean_usage_database.py instead")
    
    response = input("\n⚠️  Are you SURE you want a complete reset? (type 'RESET' to confirm): ").strip()
    
    if response == 'RESET':
        complete_usage_reset()
        print("\n🎯 Ready for fresh usage system setup!")
    else:
        print("❌ Complete reset cancelled")
        print("💡 Use clean_usage_database.py for safer cleanup")

if __name__ == "__main__":
    main()