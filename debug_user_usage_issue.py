#!/usr/bin/env python3
"""
Debug script for user usage issue
Tests the exact same flow as the backend service
"""

import os
import sys
import sqlite3
from datetime import date
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set DATA_DIR to match what backend uses
os.environ['DATA_DIR'] = str(Path(__file__).parent / "backend" / "data")

def debug_user_usage():
    """Debug the user usage breakdown issue step by step"""
    print("🔍 DEBUG: Starting user usage breakdown debugging...")
    
    # 1. Check DATA_DIR
    data_dir = os.environ.get('DATA_DIR', './data')
    db_path = f"{data_dir}/webui.db"
    print(f"🔍 DATA_DIR: {data_dir}")
    print(f"🔍 Database path: {db_path}")
    print(f"🔍 Database exists: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        return
    
    # 2. Test client organization lookup
    print(f"\n🔍 === CLIENT ORGANIZATION LOOKUP ===")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM client_organizations WHERE is_active = 1")
    active_clients = cursor.fetchall()
    print(f"🔍 Active clients: {active_clients}")
    
    if not active_clients:
        print("❌ No active client organizations found")
        conn.close()
        return
    
    client_org_id = active_clients[0][0]  # Use first active client
    print(f"🔍 Using client_org_id: {client_org_id}")
    
    # 3. Test date range calculation
    print(f"\n🔍 === DATE RANGE CALCULATION ===")
    end_date = date.today()
    start_date = end_date.replace(day=1)
    print(f"🔍 Date range: {start_date} to {end_date}")
    
    # 4. Test user usage query
    print(f"\n🔍 === USER USAGE QUERY ===")
    cursor.execute("""
        SELECT client_org_id, user_id, usage_date, total_tokens, total_requests, 
               raw_cost, markup_cost, openrouter_user_id
        FROM client_user_daily_usage 
        WHERE client_org_id = ? AND usage_date >= ? AND usage_date <= ?
        ORDER BY usage_date DESC
    """, (client_org_id, start_date.isoformat(), end_date.isoformat()))
    
    user_records = cursor.fetchall()
    print(f"🔍 Found {len(user_records)} user usage records")
    
    if user_records:
        print("🔍 Sample records:")
        for i, record in enumerate(user_records[:3]):
            print(f"  {i+1}. {record}")
    else:
        print("❌ No user usage records found")
        
        # Check if ANY records exist for this client
        cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE client_org_id = ?", (client_org_id,))
        total_records = cursor.fetchone()[0]
        print(f"🔍 Total records for client {client_org_id}: {total_records}")
        
        # Check what dates exist
        cursor.execute("SELECT DISTINCT usage_date FROM client_user_daily_usage WHERE client_org_id = ? ORDER BY usage_date", (client_org_id,))
        dates = cursor.fetchall()
        print(f"🔍 Dates with data: {[d[0] for d in dates]}")
    
    # 5. Test user aggregation (same as repository method)
    print(f"\n🔍 === USER AGGREGATION ===")
    user_totals = {}
    for record in user_records:
        client_id, user_id, usage_date, tokens, requests, raw_cost, markup_cost, openrouter_user_id = record
        
        if user_id not in user_totals:
            user_totals[user_id] = {
                'user_id': user_id,
                'openrouter_user_id': openrouter_user_id,
                'total_tokens': 0,
                'total_requests': 0,
                'raw_cost': 0.0,
                'markup_cost': 0.0,
                'days_active': set()
            }
        
        user_totals[user_id]['total_tokens'] += tokens
        user_totals[user_id]['total_requests'] += requests
        user_totals[user_id]['raw_cost'] += raw_cost
        user_totals[user_id]['markup_cost'] += markup_cost
        user_totals[user_id]['days_active'].add(usage_date)
    
    # Convert to list
    result = []
    for user_data in user_totals.values():
        user_data['days_active'] = len(user_data['days_active'])
        result.append(user_data)
    
    print(f"🔍 Aggregated user data: {len(result)} users")
    for user in result:
        print(f"  - {user['user_id']}: {user['total_tokens']} tokens, ${user['markup_cost']:.6f}")
    
    conn.close()
    
    # 6. Expected service response
    print(f"\n🔍 === EXPECTED SERVICE RESPONSE ===")
    if result:
        print("✅ Service should return success=True with user data")
        print(f"✅ Expected user_usage array length: {len(result)}")
    else:
        print("❌ Service would return success=False with empty user_usage array")
        print("❌ This matches the observed frontend behavior")
    
    return result

if __name__ == "__main__":
    debug_user_usage()