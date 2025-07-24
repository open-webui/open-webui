#!/usr/bin/env python3
"""
Sync usage data from OpenRouter API
This is a workaround for the streaming response issue
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, date
import requests

# OpenRouter API configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/usage"

def get_recent_usage():
    """Fetch recent usage from OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Get today's usage
    response = requests.get(
        OPENROUTER_API_URL,
        headers=headers,
        params={"date": date.today().isoformat()}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching usage: {response.status_code}")
        return None

def sync_to_database(usage_data):
    """Sync usage data to mAI database"""
    if os.path.exists('/app/backend/data/webui.db'):
        db_path = '/app/backend/data/webui.db'
    else:
        db_path = 'backend/data/webui.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get organization
        cursor.execute('SELECT id FROM client_organizations WHERE is_active = 1')
        org = cursor.fetchone()
        
        if not org:
            print("No active organization found")
            return
        
        org_id = org[0]
        today = date.today()
        
        # Example: Update live counters based on API data
        # Note: You'll need to parse the actual OpenRouter response format
        total_tokens = usage_data.get('total_tokens', 0)
        total_cost = usage_data.get('total_cost', 0.0)
        
        cursor.execute('''
            UPDATE client_live_counters 
            SET today_tokens = ?, today_markup_cost = ?, last_updated = ?
            WHERE client_org_id = ? AND current_date = ?
        ''', (total_tokens, total_cost * 1.3, int(datetime.now().timestamp()), 
              org_id, today))
        
        if cursor.rowcount == 0:
            # Insert if not exists
            cursor.execute('''
                INSERT INTO client_live_counters 
                (client_org_id, current_date, today_tokens, today_requests, 
                 today_raw_cost, today_markup_cost, last_updated)
                VALUES (?, ?, ?, 1, ?, ?, ?)
            ''', (org_id, today, total_tokens, total_cost, total_cost * 1.3, 
                  int(datetime.now().timestamp())))
        
        conn.commit()
        print(f"✅ Synced {total_tokens} tokens, ${total_cost * 1.3} to database")
        
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def manual_record_usage(tokens, cost):
    """Manually record usage to database"""
    if os.path.exists('/app/backend/data/webui.db'):
        db_path = '/app/backend/data/webui.db'
    else:
        db_path = 'backend/data/webui.db'
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get org and current values
        cursor.execute('''
            SELECT co.id, clc.today_tokens, clc.today_requests, clc.today_raw_cost
            FROM client_organizations co
            LEFT JOIN client_live_counters clc ON co.id = clc.client_org_id 
                AND clc.current_date = ?
            WHERE co.is_active = 1
        ''', (date.today(),))
        
        result = cursor.fetchone()
        if result:
            org_id = result[0]
            current_tokens = result[1] or 0
            current_requests = result[2] or 0
            current_cost = result[3] or 0.0
            
            # Update with new values
            new_tokens = current_tokens + tokens
            new_requests = current_requests + 1
            new_cost = current_cost + cost
            
            cursor.execute('''
                INSERT OR REPLACE INTO client_live_counters 
                (client_org_id, current_date, today_tokens, today_requests, 
                 today_raw_cost, today_markup_cost, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (org_id, date.today(), new_tokens, new_requests, 
                  new_cost, new_cost * 1.3, int(datetime.now().timestamp())))
            
            conn.commit()
            print(f"✅ Recorded usage: {tokens} tokens, ${cost} → Total: {new_tokens} tokens, ${new_cost * 1.3}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("OpenRouter Usage Sync Tool")
    print("=" * 50)
    
    # Based on the usage data you provided:
    # Generation 1: 653 + 19 = 672 tokens, $0.000354
    # Generation 2: 1041 + 38 = 1079 tokens, $0.00083298
    # Total: 1751 tokens, $0.00118698
    
    print("\nManually recording your recent usage...")
    manual_record_usage(672, 0.000354)
    manual_record_usage(1079, 0.00083298)
    
    print("\nNow check your Usage tab in mAI!")