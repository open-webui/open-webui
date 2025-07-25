#!/usr/bin/env python3
"""
Create database tables for mAI usage tracking system
"""

import sqlite3
import time
from datetime import date

DB_PATH = "backend/open_webui/data/webui.db"

def create_tables():
    """Create all necessary tables for Option 1 usage tracking"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Global Settings Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_settings (
                id TEXT PRIMARY KEY,
                openrouter_provisioning_key TEXT,
                default_markup_rate REAL DEFAULT 1.3,
                billing_currency TEXT DEFAULT 'USD',
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 2. Client Organizations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                openrouter_api_key TEXT NOT NULL UNIQUE,
                openrouter_key_hash TEXT,
                markup_rate REAL DEFAULT 1.3,
                monthly_limit REAL,
                billing_email TEXT,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 3. User Client Mapping Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_client_mapping (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                client_org_id TEXT NOT NULL,
                openrouter_user_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 4. Client Daily Usage Table
        cursor.execute('''
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
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 5. Client User Daily Usage Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_user_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                openrouter_user_id TEXT NOT NULL,
                usage_date DATE NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 6. Client Model Daily Usage Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_model_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                usage_date DATE NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                provider TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')
        
        # 7. Client Live Counters Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_live_counters (
                client_org_id TEXT PRIMARY KEY,
                current_date DATE NOT NULL,
                today_tokens INTEGER DEFAULT 0,
                today_requests INTEGER DEFAULT 0,
                today_raw_cost REAL DEFAULT 0.0,
                today_markup_cost REAL DEFAULT 0.0,
                last_updated INTEGER DEFAULT 0
            )
        ''')
        
        # 8. Processed Generations Table (for deduplication)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_generations (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                generation_date DATE NOT NULL,
                processed_at INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                total_tokens INTEGER NOT NULL
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_date ON client_daily_usage(client_org_id, usage_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_client_date ON client_user_daily_usage(client_org_id, user_id, usage_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_client_date ON client_model_daily_usage(client_org_id, model_name, usage_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_live_client ON client_live_counters(client_org_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_client_date ON processed_generations(client_org_id, generation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_generations(processed_at)')
        
        conn.commit()
        print("✅ All database tables created successfully")
        
        # Create sample data
        create_sample_data(cursor)
        conn.commit()
        print("✅ Sample data created successfully")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_sample_data(cursor):
    """Create sample data for testing"""
    current_time = int(time.time())
    today = date.today()
    
    # 1. Create default organization
    org_id = "default_org_2024"
    cursor.execute('''
        INSERT OR IGNORE INTO client_organizations 
        (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, "Default Organization", "sk-or-test-key-12345", 1.3, 1, current_time, current_time))
    
    # 2. Create user mapping (assuming user ID exists)
    cursor.execute('''
        INSERT OR IGNORE INTO user_client_mapping 
        (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ("test_user_mapping", "test_user", org_id, "openrouter_test_user", 1, current_time, current_time))
    
    # 3. Create live counter with some test data
    cursor.execute('''
        INSERT OR REPLACE INTO client_live_counters 
        (client_org_id, current_date, today_tokens, today_requests, today_raw_cost, today_markup_cost, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, today, 1751, 5, 0.00154, 0.002002, current_time))
    
    # 4. Create some historical daily data
    from datetime import timedelta
    
    for i in range(1, 8):  # Last 7 days
        test_date = today - timedelta(days=i)
        daily_id = f"{org_id}_{test_date.isoformat()}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO client_daily_usage 
            (id, client_org_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (daily_id, org_id, test_date, 1000 + (i * 200), 3, 0.001 + (i * 0.0005), 0.0013 + (i * 0.00065), current_time, current_time))
        
        # User daily usage
        user_daily_id = f"{org_id}:test_user:{test_date}"
        cursor.execute('''
            INSERT OR IGNORE INTO client_user_daily_usage 
            (id, client_org_id, user_id, openrouter_user_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_daily_id, org_id, "test_user", "openrouter_test_user", test_date, 1000 + (i * 200), 3, 0.001 + (i * 0.0005), 0.0013 + (i * 0.00065), current_time, current_time))
        
        # Model daily usage
        model_daily_id = f"{org_id}:anthropic/claude-3.5-sonnet:{test_date}"
        cursor.execute('''
            INSERT OR IGNORE INTO client_model_daily_usage 
            (id, client_org_id, model_name, usage_date, total_tokens, total_requests, raw_cost, markup_cost, provider, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model_daily_id, org_id, "anthropic/claude-3.5-sonnet", test_date, 1000 + (i * 200), 3, 0.001 + (i * 0.0005), 0.0013 + (i * 0.00065), "anthropic", current_time, current_time))

if __name__ == "__main__":
    create_tables()