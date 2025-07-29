#!/usr/bin/env python3
"""
Debug script to simulate the complete user usage API call
"""
import sys
import os
import sqlite3
from datetime import date

# Add the project root to sys.path
sys.path.append('/Users/patpil/Documents/Projects/mAI/backend')

def debug_database_state():
    """Debug the current database state"""
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    
    print("=== DATABASE STATE DEBUG ===")
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check client organizations
        cursor.execute("SELECT id, name, is_active FROM client_organizations")
        orgs = cursor.fetchall()
        print(f"\nClient Organizations ({len(orgs)}):")
        for org in orgs:
            print(f"  - {org[0]}: {org[1]} (active: {org[2]})")
        
        # Check aggregate usage
        cursor.execute("""
            SELECT client_org_id, usage_date, total_tokens, total_requests, markup_cost 
            FROM client_daily_usage 
            ORDER BY usage_date DESC LIMIT 5
        """)
        daily_usage = cursor.fetchall()
        print(f"\nClientDailyUsage ({len(daily_usage)} recent records):")
        for usage in daily_usage:
            print(f"  - {usage[0]}: {usage[1]} | {usage[2]} tokens | {usage[3]} requests | ${usage[4]}")
        
        # Check user-level usage
        cursor.execute("""
            SELECT client_org_id, user_id, usage_date, total_tokens, total_requests, markup_cost 
            FROM client_user_daily_usage 
            ORDER BY usage_date DESC LIMIT 5
        """)
        user_usage = cursor.fetchall()
        print(f"\nClientUserDailyUsage ({len(user_usage)} recent records):")
        for usage in user_usage:
            print(f"  - {usage[0]} | {usage[1]}: {usage[2]} | {usage[3]} tokens | {usage[4]} requests | ${usage[5]}")
        
        # Test the specific query that get_usage_by_user would run
        end_date = date.today()
        start_date = end_date.replace(day=1)
        
        cursor.execute("""
            SELECT client_org_id, user_id, usage_date, total_tokens, total_requests, markup_cost 
            FROM client_user_daily_usage 
            WHERE client_org_id = ? AND usage_date >= ? AND usage_date <= ?
        """, ("dev_mai_client_d460a478", start_date, end_date))
        filtered_usage = cursor.fetchall()
        print(f"\nFiltered User Usage for dev_mai_client_d460a478 ({start_date} to {end_date}):")
        print(f"Found {len(filtered_usage)} records:")
        for usage in filtered_usage:
            print(f"  - {usage[0]} | {usage[1]}: {usage[2]} | {usage[3]} tokens | {usage[4]} requests | ${usage[5]}")
        
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

def simulate_get_environment_client_id():
    """Simulate the get_environment_client_id logic"""
    print("\n=== CLIENT ID RESOLUTION DEBUG ===")
    
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name FROM client_organizations WHERE is_active = 1 ORDER BY id")
        orgs = cursor.fetchall()
        
        if orgs:
            client_id = orgs[0][0]
            print(f"First active client (would be returned): {client_id}")
            return client_id
        else:
            print("No active clients found")
            return None
    finally:
        conn.close()

def simulate_user_usage_query():
    """Simulate the complete user usage query process"""
    print("\n=== USER USAGE QUERY SIMULATION ===")
    
    # Get client ID
    client_org_id = simulate_get_environment_client_id()
    if not client_org_id:
        print("Cannot proceed without client_org_id")
        return
    
    # Simulate the date range calculation
    end_date = date.today()
    start_date = end_date.replace(day=1)
    print(f"Date range: {start_date} to {end_date}")
    
    # Query the database like get_usage_by_user does
    db_path = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT user_id, openrouter_user_id, usage_date, total_tokens, total_requests, markup_cost
            FROM client_user_daily_usage 
            WHERE client_org_id = ? AND usage_date >= ? AND usage_date <= ?
        """, (client_org_id, start_date, end_date))
        
        user_records = cursor.fetchall()
        print(f"Query result: {len(user_records)} records found")
        
        # Aggregate by user (like the actual method does)
        user_totals = {}
        for record in user_records:
            user_id = record[0]
            if user_id not in user_totals:
                user_totals[user_id] = {
                    'user_id': user_id,
                    'openrouter_user_id': record[1],
                    'total_tokens': 0,
                    'total_requests': 0,
                    'markup_cost': 0.0,
                }
            user_totals[user_id]['total_tokens'] += record[3]
            user_totals[user_id]['total_requests'] += record[4]
            user_totals[user_id]['markup_cost'] += record[5]
        
        print(f"Aggregated users: {len(user_totals)}")
        for user_id, data in user_totals.items():
            print(f"  - {user_id}: {data['total_tokens']} tokens, {data['total_requests']} requests, ${data['markup_cost']}")
            
        return len(user_totals) > 0
        
    finally:
        conn.close()

if __name__ == "__main__":
    debug_database_state()
    has_user_data = simulate_user_usage_query()
    
    print(f"\n=== CONCLUSION ===")
    print(f"User usage data found: {has_user_data}")
    if has_user_data:
        print("✅ The By User tab SHOULD show data based on current database state")
        print("❓ If the frontend shows no data, there may be an API call issue or different environment")
    else:
        print("❌ No user usage data found - this explains the empty By User tab")