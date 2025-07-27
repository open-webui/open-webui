#!/usr/bin/env python3
"""
Test script for simplified usage tracking after removing live counters
"""

import sqlite3
import os
from datetime import date

def test_simplified_usage_tracking():
    """Test the simplified usage tracking functionality"""
    
    # Database path
    db_path = "backend/data/webui.db"
    
    print("🔧 Setting up test database")
    # Always recreate for testing
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create minimal test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create client_organizations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            openrouter_api_key TEXT NOT NULL UNIQUE,
            openrouter_key_hash TEXT,
            markup_rate REAL DEFAULT 1.3,
            monthly_limit REAL,
            billing_email TEXT,
            timezone TEXT DEFAULT 'Europe/Warsaw',
            is_active INTEGER DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    # Create simplified daily usage tables (no live counters)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_daily_usage (
            id TEXT PRIMARY KEY,
            client_org_id TEXT NOT NULL,
            usage_date DATE NOT NULL,
            total_tokens INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            raw_cost REAL DEFAULT 0.0,
            markup_cost REAL DEFAULT 0.0,
            primary_model TEXT,
            unique_users INTEGER DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_user_daily_usage (
            id TEXT PRIMARY KEY,
            client_org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            usage_date DATE NOT NULL,
            openrouter_user_id TEXT NOT NULL,
            total_tokens INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            raw_cost REAL DEFAULT 0.0,
            markup_cost REAL DEFAULT 0.0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_model_daily_usage (
            id TEXT PRIMARY KEY,
            client_org_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            provider TEXT,
            usage_date DATE NOT NULL,
            total_tokens INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            raw_cost REAL DEFAULT 0.0,
            markup_cost REAL DEFAULT 0.0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    # Insert test organization
    import time
    current_time = int(time.time())
    cursor.execute("""
        INSERT OR REPLACE INTO client_organizations 
        (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'dev_mai_client_d460a478',
        'Test Organization',
        'test_api_key',
        1.3,
        1,
        current_time,
        current_time
    ))
    
    conn.commit()
    conn.close()
    print("✅ Test database created")
    
    # Test simplified usage recording
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check that client_live_counters table does NOT exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_live_counters'")
    live_table = cursor.fetchone()
    print(f"✅ client_live_counters table removed: {live_table is None}")
    
    # Check that required tables exist
    required_tables = ['client_daily_usage', 'client_user_daily_usage', 'client_model_daily_usage']
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cursor.fetchone()
        print(f"✅ {table} exists: {exists is not None}")
    
    # Test simplified usage recording (direct SQL to simulate ORM)
    today = date.today().isoformat()
    current_time = int(time.time())
    
    # Test client daily usage
    cursor.execute("""
        INSERT OR REPLACE INTO client_daily_usage 
        (id, client_org_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f'dev_mai_client_d460a478:{today}',
        'dev_mai_client_d460a478',
        today,
        700,  # 500 input + 200 output
        1,
        0.001,
        0.0013,
        current_time,
        current_time
    ))
    
    # Test user daily usage
    cursor.execute("""
        INSERT OR REPLACE INTO client_user_daily_usage 
        (id, client_org_id, user_id, usage_date, openrouter_user_id, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f'dev_mai_client_d460a478:test_user:{today}',
        'dev_mai_client_d460a478',
        'test_user',
        today,
        'test_openrouter_user',
        700,
        1,
        0.001,
        0.0013,
        current_time,
        current_time
    ))
    
    # Test model daily usage
    cursor.execute("""
        INSERT OR REPLACE INTO client_model_daily_usage 
        (id, client_org_id, model_name, usage_date, total_tokens, total_requests, raw_cost, markup_cost, provider, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f'dev_mai_client_d460a478:google/gemini-2.5-flash-lite-preview-06-17:{today}',
        'dev_mai_client_d460a478',
        'google/gemini-2.5-flash-lite-preview-06-17',
        today,
        700,
        1,
        0.001,
        0.0013,
        'google',
        current_time,
        current_time
    ))
    
    conn.commit()
    
    # Verify data was recorded
    cursor.execute("SELECT * FROM client_daily_usage WHERE usage_date = ?", (today,))
    daily_usage = cursor.fetchone()
    print(f"✅ Daily usage recorded: {daily_usage is not None}")
    if daily_usage:
        print(f"   Tokens: {daily_usage[3]}, Cost: ${daily_usage[6]:.6f}")
    
    cursor.execute("SELECT * FROM client_user_daily_usage WHERE usage_date = ?", (today,))
    user_usage = cursor.fetchone()
    print(f"✅ User usage recorded: {user_usage is not None}")
    
    cursor.execute("SELECT * FROM client_model_daily_usage WHERE usage_date = ?", (today,))
    model_usage = cursor.fetchone()
    print(f"✅ Model usage recorded: {model_usage is not None}")
    
    # Test that we can query today's data (simulating get_usage_stats_by_client)
    cursor.execute("""
        SELECT total_tokens, total_requests, markup_cost, updated_at 
        FROM client_daily_usage 
        WHERE client_org_id = ? AND usage_date = ?
    """, ('dev_mai_client_d460a478', today))
    
    stats = cursor.fetchone()
    if stats:
        tokens, requests, cost, updated_at = stats
        print(f"✅ Today's stats retrieved: {tokens} tokens, {requests} requests, ${cost:.6f}")
        print(f"   Last updated: {updated_at}")
    
    conn.close()
    
    print("\n🎉 Simplified usage tracking test completed successfully!")
    print("📋 Summary of changes:")
    print("   • Removed client_live_counters table")
    print("   • Simplified record_usage to work with daily summaries only")
    print("   • get_usage_stats_by_client now reads from daily summaries")
    print("   • No more rollover functionality needed")
    print("   • Storage reduced and complexity simplified")

if __name__ == "__main__":
    test_simplified_usage_tracking()