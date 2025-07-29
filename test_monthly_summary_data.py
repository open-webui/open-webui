#!/usr/bin/env python3
"""
Test script to simulate the exact data structure expected by the frontend
"""

import sqlite3
from datetime import date

def simulate_monthly_summary():
    """Simulate what the monthly summary should look like"""
    
    # Connect to database
    DB_PATH = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get current month boundaries
        today = date.today()
        current_month_start = today.replace(day=1).isoformat()
        client_org_id = "dev_mai_client_d460a478"
        
        print(f"🔍 Simulating monthly summary for {client_org_id}")
        print(f"📅 Date range: {current_month_start} to {today.isoformat()}")
        print("-" * 60)
        
        # 1. Calculate top models (same logic as backend)
        print("1️⃣ Calculating top models...")
        cursor.execute("""
            SELECT model_name, SUM(total_tokens) as total_tokens
            FROM client_model_daily_usage 
            WHERE client_org_id = ? 
              AND usage_date >= ? 
              AND usage_date <= ?
            GROUP BY model_name 
            ORDER BY total_tokens DESC 
            LIMIT 3
        """, (client_org_id, current_month_start, today.isoformat()))
        
        model_records = cursor.fetchall()
        top_models = []
        for record in model_records:
            top_models.append({
                'model_name': record[0],
                'total_tokens': record[1]
            })
        
        print(f"✅ Top models: {top_models}")
        
        # 2. Calculate unique users (same logic as backend)
        print("\n2️⃣ Calculating unique users...")
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as unique_users
            FROM client_user_daily_usage 
            WHERE client_org_id = ? 
              AND usage_date >= ? 
              AND usage_date <= ?
        """, (client_org_id, current_month_start, today.isoformat()))
        
        user_result = cursor.fetchone()
        total_unique_users = user_result[0] if user_result else 0
        
        print(f"✅ Unique users: {total_unique_users}")
        
        # 3. Simulate the complete monthly_summary structure
        print("\n3️⃣ Complete monthly_summary structure:")
        monthly_summary = {
            'average_daily_tokens': 0,
            'average_daily_cost': 0,
            'average_usage_day_tokens': 0,
            'busiest_day': None,
            'highest_cost_day': None,
            'total_unique_users': total_unique_users,
            'top_models': top_models
        }
        
        print(f"✅ monthly_summary: {monthly_summary}")
        
        # 4. Test the frontend condition
        print("\n4️⃣ Testing frontend conditions:")
        has_top_models = bool(monthly_summary.get('top_models'))
        has_top_models_length = len(monthly_summary.get('top_models', [])) > 0
        condition_result = has_top_models and has_top_models_length
        
        print(f"   monthly_summary?.top_models: {has_top_models}")
        print(f"   monthly_summary.top_models.length > 0: {has_top_models_length}")
        print(f"   Combined condition: {condition_result}")
        
        if condition_result:
            print("✅ Monthly summary section SHOULD be visible")
        else:
            print("❌ Monthly summary section will NOT be visible")
            
        # 5. Complete stats structure
        print("\n5️⃣ Complete stats structure that should be sent to frontend:")
        complete_stats = {
            'current_month': {
                'month': today.strftime('%B %Y'),
                'total_tokens': 700,
                'total_cost': 0.001,
                'total_cost_pln': 0.004,
                'total_requests': 1,
                'days_with_usage': 1,
                'days_in_month': today.day,
                'usage_percentage': 100.0 / today.day
            },
            'daily_breakdown': [
                {
                    'date': '2025-07-27',
                    'day_name': 'Sunday', 
                    'tokens': 700,
                    'cost': 0.001,
                    'cost_pln': 0.004,
                    'requests': 1,
                    'primary_model': 'google/gemini-2.5-flash-lite-preview-06-17',
                    'last_activity': '12:00'
                }
            ],
            'monthly_summary': monthly_summary,
            'client_org_name': 'Test Organization'
        }
        
        print("✅ Frontend should receive this structure in usageData:")
        import json
        print(json.dumps(complete_stats, indent=2))
        
    finally:
        conn.close()

if __name__ == "__main__":
    simulate_monthly_summary()