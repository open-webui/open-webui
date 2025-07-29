#!/usr/bin/env python3
"""
Clean test_user data from open_webui/data/webui.db
=================================================

This script removes test_user data from the second database file.
"""

import sqlite3
from datetime import datetime

def clean_test_data():
    """Clean test_user data from the open_webui database."""
    
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/open_webui/data/webui.db"
    
    print(f"🚀 Cleaning test_user data from: {db_path}")
    print("=" * 60)
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check current test_user data
            print("📊 Current test_user data:")
            cursor.execute("""
                SELECT usage_date, total_tokens, raw_cost, markup_cost 
                FROM client_user_daily_usage 
                WHERE user_id = 'test_user' 
                ORDER BY usage_date DESC
            """)
            
            test_records = cursor.fetchall()
            total_tokens = 0
            total_cost = 0
            
            for record in test_records:
                cost = record['raw_cost'] + record['markup_cost']
                total_tokens += record['total_tokens']
                total_cost += cost
                print(f"   {record['usage_date']}: {record['total_tokens']} tokens, ${cost:.6f}")
            
            print(f"\n📈 Total test_user usage: {total_tokens} tokens, ${total_cost:.6f}")
            
            # Clean test_user data
            print("\n🧹 Cleaning test_user data...")
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Delete from client_user_daily_usage
            cursor.execute("DELETE FROM client_user_daily_usage WHERE user_id = 'test_user'")
            user_deleted = cursor.rowcount
            print(f"   ✅ Deleted {user_deleted} records from client_user_daily_usage")
            
            # Clean related client_daily_usage records for test client
            cursor.execute("""
                DELETE FROM client_daily_usage 
                WHERE client_org_id = 'default_org_2024'
                AND NOT EXISTS (
                    SELECT 1 FROM client_user_daily_usage 
                    WHERE client_org_id = 'default_org_2024'
                    AND user_id != 'test_user'
                )
            """)
            client_deleted = cursor.rowcount
            print(f"   ✅ Deleted {client_deleted} records from client_daily_usage")
            
            # Clean related client_model_daily_usage records
            cursor.execute("""
                DELETE FROM client_model_daily_usage 
                WHERE client_org_id = 'default_org_2024'
                AND NOT EXISTS (
                    SELECT 1 FROM client_user_daily_usage 
                    WHERE client_org_id = 'default_org_2024'
                    AND user_id != 'test_user'
                )
            """)
            model_deleted = cursor.rowcount
            print(f"   ✅ Deleted {model_deleted} records from client_model_daily_usage")
            
            # Commit changes
            conn.commit()
            print(f"\n✅ Successfully cleaned test_user data!")
            
            # Verify cleanup
            print("\n🔍 Verifying cleanup...")
            cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE user_id = 'test_user'")
            remaining = cursor.fetchone()[0]
            
            if remaining == 0:
                print("   ✅ No test_user records remain")
            else:
                print(f"   ⚠️  {remaining} test_user records still exist")
            
            # Check remaining data
            cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage")
            total_remaining = cursor.fetchone()[0]
            print(f"   📊 {total_remaining} total user usage records remain")
            
            cursor.execute("SELECT COUNT(*) FROM client_daily_usage")
            daily_remaining = cursor.fetchone()[0]
            print(f"   📊 {daily_remaining} daily usage records remain")
            
            cursor.execute("SELECT COUNT(*) FROM client_model_daily_usage")
            model_remaining = cursor.fetchone()[0]
            print(f"   📊 {model_remaining} model usage records remain")
            
            return {
                "success": True,
                "deleted": {
                    "user_records": user_deleted,
                    "client_records": client_deleted,
                    "model_records": model_deleted
                },
                "test_user_tokens": total_tokens,
                "test_user_cost": total_cost
            }
            
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    result = clean_test_data()
    
    if result["success"]:
        print(f"\n🎉 Cleanup completed successfully!")
        print(f"   Removed {result['test_user_tokens']} test tokens")
        print(f"   Removed ${result['test_user_cost']:.6f} test cost")
    else:
        print(f"\n❌ Cleanup failed: {result['error']}")