#!/usr/bin/env python3
"""
Verify if recent OpenRouter queries are tracked in the usage database
"""

import sqlite3
import json
from datetime import datetime, date

def verify_recent_usage():
    print("=== Verifying Recent Usage in Database ===")
    print()
    
    # Query data from user
    query1 = {
        "generation_id": "gen-1753473140-nGp5E5fmE4fZRwapci2P",
        "model": "google/gemini-2.5-flash-lite-preview-06-17",
        "external_user": "mai_client_63a4eb6d_user_d0789b57",
        "tokens_total": 1544 + 25,  # prompt + completion
        "usage": 0.0001724,
        "created_at": "2025-07-25T19:52:22.364378+00:00"
    }
    
    query2 = {
        "generation_id": "gen-1753473182-d6QqpxBsaRV6c3A3Pj2U",
        "model": "openai/gpt-4o-mini",
        "external_user": "mai_client_63a4eb6d_user_d0789b57",
        "tokens_total": 2590 + 69,  # prompt + completion
        "usage": 0.0004266,
        "created_at": "2025-07-25T19:53:04.690798+00:00"
    }
    
    queries = [query1, query2]
    
    print("🔍 Looking for these OpenRouter queries:")
    for i, query in enumerate(queries, 1):
        print(f"   {i}. Model: {query['model']}")
        print(f"      Generation ID: {query['generation_id']}")
        print(f"      External User: {query['external_user']}")
        print(f"      Tokens: {query['tokens_total']}")
        print(f"      Cost: ${query['usage']:.6f}")
        print(f"      Time: {query['created_at']}")
        print()
    
    # Check database
    db_path = "backend/data/webui.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Database Analysis:")
        print("-" * 80)
        
        # 1. Check processed_generations table
        print("1. Checking processed_generations table:")
        
        for i, query in enumerate(queries, 1):
            cursor.execute("""
                SELECT id, client_org_id, generation_date, processed_at, total_cost, total_tokens
                FROM processed_generations 
                WHERE id = ?
            """, (query['generation_id'],))
            
            result = cursor.fetchone()
            if result:
                print(f"   Query {i}: ✅ FOUND - ID: {result[0]}, Cost: ${result[4]:.6f}, Tokens: {result[5]}")
            else:
                print(f"   Query {i}: ❌ NOT FOUND - {query['generation_id']}")
        
        print()
        
        # 2. Check client_user_daily_usage table
        print("2. Checking client_user_daily_usage table:")
        today = date.today()
        
        cursor.execute("""
            SELECT client_org_id, user_id, openrouter_user_id, usage_date, 
                   total_tokens, total_requests, raw_cost, markup_cost
            FROM client_user_daily_usage 
            WHERE usage_date = ? AND openrouter_user_id LIKE '%user_d0789b57%'
        """, (today,))
        
        user_usage = cursor.fetchall()
        if user_usage:
            for row in user_usage:
                print(f"   ✅ User usage found: Client: {row[0]}, User: {row[1]}")
                print(f"      Tokens: {row[4]}, Requests: {row[5]}, Cost: ${row[7]:.6f}")
        else:
            print(f"   ❌ No user usage found for today ({today}) with user_d0789b57")
        
        print()
        
        # 3. Check client_model_daily_usage table
        print("3. Checking client_model_daily_usage table:")
        
        for model in ["google/gemini-2.5-flash-lite-preview-06-17", "openai/gpt-4o-mini"]:
            cursor.execute("""
                SELECT client_org_id, model_name, usage_date, 
                       total_tokens, total_requests, raw_cost, markup_cost
                FROM client_model_daily_usage 
                WHERE usage_date = ? AND model_name = ?
            """, (today, model))
            
            model_usage = cursor.fetchone()
            if model_usage:
                print(f"   ✅ Model usage found: {model}")
                print(f"      Tokens: {model_usage[3]}, Requests: {model_usage[4]}, Cost: ${model_usage[6]:.6f}")
            else:
                print(f"   ❌ No usage found for model: {model}")
        
        print()
        
        # 4. Check if client organization exists
        print("4. Checking client organization:")
        
        # Try to find client org by external_user pattern
        client_prefix = "mai_client_63a4eb6d"
        cursor.execute("""
            SELECT id, name, is_active, openrouter_api_key
            FROM client_organizations 
            WHERE id LIKE ?
        """, (f"{client_prefix}%",))
        
        client_org = cursor.fetchone()
        if client_org:
            print(f"   ✅ Client org found: {client_org[0]} - {client_org[1]} (Active: {client_org[2]})")
            has_api_key = "Yes" if client_org[3] else "No"
            print(f"      Has OpenRouter API key: {has_api_key}")
        else:
            print(f"   ❌ No client organization found with prefix: {client_prefix}")
        
        print()
        
        # 5. Check recent activity summary
        print("5. Recent database activity summary:")
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM processed_generations")
        total_generations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE usage_date = ?", (today,))
        today_user_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM client_model_daily_usage WHERE usage_date = ?", (today,))
        today_model_records = cursor.fetchone()[0]
        
        print(f"   • Total processed generations: {total_generations}")
        print(f"   • Today's user usage records: {today_user_records}")
        print(f"   • Today's model usage records: {today_model_records}")
        
        # Check most recent activity
        cursor.execute("""
            SELECT id, generation_date, total_cost, total_tokens 
            FROM processed_generations 
            ORDER BY processed_at DESC 
            LIMIT 5
        """)
        recent = cursor.fetchall()
        
        if recent:
            print(f"   • Most recent 5 processed generations:")
            for gen in recent:
                print(f"     - {gen[0]} | {gen[1]} | ${gen[2]:.6f} | {gen[3]} tokens")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    print("-" * 80)
    return True

def analyze_tracking_issues():
    print("\n🔍 ANALYSIS: Why queries might not be tracked")
    print()
    
    print("Possible reasons for missing usage data:")
    print("1. ❓ OpenRouter webhook not configured or not working")
    print("2. ❓ Manual sync not run recently (/sync/openrouter-usage)")
    print("3. ❓ Client organization setup incomplete")
    print("4. ❓ User mapping not properly configured")
    print("5. ❓ Database cleanup removed all records recently")
    print()
    
    print("Next steps to enable tracking:")
    print("✅ 1. Set up client organization with proper mai_client_ prefix")
    print("✅ 2. Configure OpenRouter API key for the client")
    print("✅ 3. Set up user mapping service")
    print("✅ 4. Run manual sync or configure webhook")

if __name__ == "__main__":
    print("🔍 Checking if recent OpenRouter queries are tracked in mAI database...")
    print()
    
    success = verify_recent_usage()
    analyze_tracking_issues()
    
    if success:
        print("\n📋 Database verification completed!")
    else:
        print("\n❌ Database verification failed!")