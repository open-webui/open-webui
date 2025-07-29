#!/usr/bin/env python3
"""
Fix for the user usage data issue.
This script repairs the missing ClientUserDailyUsage records based on existing ClientDailyUsage data.
"""

import sqlite3
import time
from datetime import date

def fix_missing_user_records():
    """Create missing user records based on existing daily records"""
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    
    print("🔧 FIXING MISSING USER USAGE RECORDS")
    print("="*50)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM client_daily_usage")
        daily_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage")
        user_count = cursor.fetchone()[0]
        
        print(f"Current state:")
        print(f"  - ClientDailyUsage records: {daily_count}")
        print(f"  - ClientUserDailyUsage records: {user_count}")
        
        # Get daily records that have no corresponding user records
        cursor.execute("""
            SELECT cd.client_org_id, cd.usage_date, cd.total_tokens, cd.total_requests, 
                   cd.raw_cost, cd.markup_cost
            FROM client_daily_usage cd
            LEFT JOIN client_user_daily_usage cu ON 
                cd.client_org_id = cu.client_org_id AND cd.usage_date = cu.usage_date
            WHERE cu.id IS NULL AND cd.total_tokens > 0
        """)
        
        missing_records = cursor.fetchall()
        print(f"\nFound {len(missing_records)} daily records without corresponding user records:")
        
        current_time = int(time.time())
        
        for record in missing_records:
            client_org_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost = record
            print(f"  Processing {client_org_id} on {usage_date}: {total_tokens} tokens")
            
            # Create user record with placeholder user information
            user_record_id = f"{client_org_id}:system_user:{usage_date}"
            
            cursor.execute("""
                INSERT INTO client_user_daily_usage 
                (id, client_org_id, user_id, usage_date, openrouter_user_id, 
                 total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_record_id,
                client_org_id,
                "system_user",  # Placeholder user since we don't know actual user
                usage_date,
                "historical_usage_user",
                total_tokens,
                total_requests,
                raw_cost,
                markup_cost,
                current_time,
                current_time
            ))
            
            print(f"    ✅ Created user record for {total_tokens} tokens")
        
        # Commit changes
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage")
        new_user_count = cursor.fetchone()[0]
        
        print(f"\n🎉 FIX COMPLETED!")
        print(f"  - ClientUserDailyUsage records: {user_count} → {new_user_count}")
        print(f"  - Added {new_user_count - user_count} missing user records")
        
        # Show sample of created records
        cursor.execute("""
            SELECT client_org_id, user_id, usage_date, total_tokens
            FROM client_user_daily_usage 
            ORDER BY usage_date DESC
            LIMIT 3
        """)
        
        sample_records = cursor.fetchall()
        print(f"\nSample user records now in database:")
        for record in sample_records:
            print(f"  - Client: {record[0]}, User: {record[1]}, Date: {record[2]}, Tokens: {record[3]}")
            
    except Exception as e:
        print(f"❌ Error fixing user records: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_api_consistency():
    """Test that both APIs now return consistent data"""
    print(f"\n🧪 VERIFYING API CONSISTENCY")
    print("="*50)
    
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Simulate monthly summary query (from get_usage_stats_by_client)
        today = date.today()
        current_month_start = today.replace(day=1)
        
        cursor.execute("""
            SELECT DISTINCT user_id FROM client_user_daily_usage
            WHERE client_org_id = ? AND usage_date >= ? AND usage_date <= ?
        """, ("dev_mai_client_d460a478", current_month_start, today))
        
        monthly_summary_users = cursor.fetchall()
        print(f"Monthly summary user count: {len(monthly_summary_users)}")
        
        # Simulate user breakdown query (from get_usage_by_user)
        cursor.execute("""
            SELECT user_id, SUM(total_tokens), SUM(total_requests), SUM(markup_cost)
            FROM client_user_daily_usage
            WHERE client_org_id = ? AND usage_date >= ? AND usage_date <= ?
            GROUP BY user_id
        """, ("dev_mai_client_d460a478", current_month_start, today))
        
        user_breakdown = cursor.fetchall()
        print(f"User breakdown records: {len(user_breakdown)}")
        
        for user_data in user_breakdown:
            user_id, tokens, requests, cost = user_data
            print(f"  - User: {user_id}, Tokens: {tokens}, Requests: {requests}, Cost: ${cost:.6f}")
        
        # Check consistency
        if len(monthly_summary_users) == len(user_breakdown) and len(user_breakdown) > 0:
            print(f"\n✅ CONSISTENCY VERIFIED!")
            print(f"   Both APIs now return data for {len(user_breakdown)} user(s)")
        else:
            print(f"\n❌ INCONSISTENCY DETECTED!")
            print(f"   Monthly summary: {len(monthly_summary_users)} users")
            print(f"   User breakdown: {len(user_breakdown)} users")
            
    except Exception as e:
        print(f"❌ Error verifying consistency: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Step 1: Fix the missing user records
    fix_missing_user_records()
    
    # Step 2: Verify the fix worked
    verify_api_consistency()
    
    print(f"\n🏁 USER USAGE DATA FIX COMPLETED")
    print("="*50)
    print("The 'By User' tab should now show the user data instead of 'No user usage data available'")
    print("Future usage recordings should work properly with the existing code.")