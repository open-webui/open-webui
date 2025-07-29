#!/usr/bin/env python3
"""
Debug script to check database directly for monthly summary data
"""

import sqlite3
import os
from datetime import date, datetime

# Database path
DB_PATH = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"

def check_database():
    """Check database directly for usage data"""
    print("🔍 Checking database directly...")
    print(f"Database: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    print("-" * 50)
    
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%usage%'")
        tables = cursor.fetchall()
        print(f"📊 Usage tables found: {[t[0] for t in tables]}")
        
        # Get current month boundaries
        today = date.today()
        current_month_start = today.replace(day=1).isoformat()
        
        print(f"\n📅 Current month: {current_month_start} to {today.isoformat()}")
        
        # Check ClientDailyUsage
        print("\n1️⃣ Checking ClientDailyUsage...")
        cursor.execute("""
            SELECT client_org_id, usage_date, total_tokens, total_requests, markup_cost 
            FROM client_daily_usage 
            WHERE usage_date >= ? AND usage_date <= ?
            ORDER BY usage_date DESC
            LIMIT 10
        """, (current_month_start, today.isoformat()))
        daily_usage = cursor.fetchall()
        
        if daily_usage:
            print(f"✅ Found {len(daily_usage)} daily records:")
            for record in daily_usage:
                print(f"   {record[0]} | {record[1]} | {record[2]} tokens | {record[3]} requests | ${record[4]:.6f}")
        else:
            print("❌ No daily usage records found for current month")
        
        # Check ClientModelDailyUsage
        print("\n2️⃣ Checking ClientModelDailyUsage...")
        cursor.execute("""
            SELECT client_org_id, model_name, SUM(total_tokens) as total_tokens
            FROM client_model_daily_usage 
            WHERE usage_date >= ? AND usage_date <= ?
            GROUP BY client_org_id, model_name
            ORDER BY total_tokens DESC
            LIMIT 10
        """, (current_month_start, today.isoformat()))
        model_usage = cursor.fetchall()
        
        if model_usage:
            print(f"✅ Found {len(model_usage)} model records:")
            for record in model_usage:
                print(f"   {record[0]} | {record[1]} | {record[2]} tokens")
        else:
            print("❌ No model usage records found for current month")
        
        # Check ClientUserDailyUsage
        print("\n3️⃣ Checking ClientUserDailyUsage...")
        cursor.execute("""
            SELECT client_org_id, COUNT(DISTINCT user_id) as unique_users
            FROM client_user_daily_usage 
            WHERE usage_date >= ? AND usage_date <= ?
            GROUP BY client_org_id
        """, (current_month_start, today.isoformat()))
        user_usage = cursor.fetchall()
        
        if user_usage:
            print(f"✅ Found {len(user_usage)} client records:")
            for record in user_usage:
                print(f"   {record[0]} | {record[1]} unique users")
        else:
            print("❌ No user usage records found for current month")
        
        # Check client organizations
        print("\n4️⃣ Checking ClientOrganization...")
        cursor.execute("SELECT id, name, markup_rate FROM client_organization WHERE active = 1")
        orgs = cursor.fetchall()
        
        if orgs:
            print(f"✅ Found {len(orgs)} active organizations:")
            for org in orgs:
                print(f"   {org[0]} | {org[1]} | markup: {org[2]}")
        else:
            print("❌ No active organizations found")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()