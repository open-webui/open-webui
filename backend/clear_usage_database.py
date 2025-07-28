#!/usr/bin/env python3
"""
Clear all usage tracking data for fresh testing
Safely removes all usage data while preserving structure
"""

import sys
import sqlite3

def clear_usage_database():
    """Clear all usage tracking data from database"""
    
    print("🧹 Clearing Usage Database for Fresh Testing")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    try:
        # Tables to clear (in order to respect foreign key constraints)
        tables_to_clear = [
            'client_user_daily_usage',
            'client_model_daily_usage', 
            'client_daily_usage',
            'processed_generations',
            'processed_generation_cleanup_log'
        ]
        
        print("📋 Clearing usage tracking tables...")
        
        for table in tables_to_clear:
            # Check if table exists and get current count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            current_count = cursor.fetchone()[0]
            
            # Clear the table
            cursor.execute(f"DELETE FROM {table}")
            
            print(f"  🗑️  {table}: {current_count} records → 0 records")
        
        # Commit changes
        conn.commit()
        
        print()
        print("✅ Database clearing completed!")
        
        # Verify all tables are empty
        print("\n🔍 Verification - Confirming all tables are empty:")
        all_empty = True
        
        for table in tables_to_clear:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            status = "✅ Empty" if count == 0 else f"❌ Contains {count} records"
            print(f"  {status}: {table}")
            if count > 0:
                all_empty = False
        
        print()
        if all_empty:
            print("🎉 SUCCESS: All usage tables are now empty!")
            print("📊 Database is ready for fresh testing")
        else:
            print("❌ WARNING: Some tables still contain data")
            
        return all_empty
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False
        
    finally:
        conn.close()

def show_database_status():
    """Show current database status for confirmation"""
    
    print("\n📊 Current Database Status:")
    print("=" * 40)
    
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    try:
        # Check each usage table
        tables = [
            'client_daily_usage',
            'client_user_daily_usage', 
            'client_model_daily_usage',
            'processed_generations'
        ]
        
        total_records = 0
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"  📦 {table}: {count} records")
        
        print(f"\n📈 Total usage records: {total_records}")
        
        if total_records == 0:
            print("✅ Database is completely clean - ready for testing!")
        else:
            print("⚠️  Database contains existing data")
            
        return total_records == 0
        
    except Exception as e:
        print(f"❌ Error checking database status: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Usage Database Testing Preparation")
    print("This will clear ALL usage tracking data for fresh testing")
    print()
    
    # Show current status
    show_database_status()
    
    print("\n" + "="*60)
    print("PROCEEDING WITH DATABASE CLEARING...")
    print("="*60)
    
    # Clear the database
    success = clear_usage_database()
    
    if success:
        print("\n🎯 READY FOR TESTING!")
        print("👉 Next step: Make an OpenRouter query to test the fix")
        print("📋 The system will now correctly capture:")
        print("   - tokens_prompt + tokens_completion = total_tokens")
        print("   - total_cost with proper 1.3x markup")
        print("   - Real-time database updates")
    else:
        print("\n❌ CLEARING FAILED!")
        print("🔧 Manual intervention may be required")