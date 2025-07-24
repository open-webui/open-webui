#!/usr/bin/env python3
"""
Apply the client usage tracking migration manually.
This script creates all necessary tables for the usage tracking system.
"""

import sqlite3
import time
import uuid
from pathlib import Path

def apply_migration():
    """Apply the client usage tracking migration to create necessary tables"""
    
    # Connect to the database
    db_path = Path("backend/open_webui/data/webui.db")
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_organizations'")
        if cursor.fetchone():
            print("⚠️  Tables already exist. Skipping migration.")
            return True
        
        print("📦 Creating client usage tracking tables...")
        
        # Create global_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_settings (
                id TEXT PRIMARY KEY,
                openrouter_provisioning_key TEXT,
                default_markup_rate REAL DEFAULT 1.3,
                billing_currency TEXT DEFAULT 'USD',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        ''')
        print("✅ Created global_settings table")
        
        # Create client_organizations table
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
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        ''')
        print("✅ Created client_organizations table")
        
        # Create user_client_mapping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_client_mapping (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                client_org_id TEXT NOT NULL,
                openrouter_user_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations (id)
            )
        ''')
        print("✅ Created user_client_mapping table")
        
        # Create client_live_counters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_live_counters (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                last_reset_date TEXT,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations (id)
            )
        ''')
        print("✅ Created client_live_counters table")
        
        # Create client_user_daily_usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_user_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations (id),
                UNIQUE(client_org_id, user_id, usage_date)
            )
        ''')
        print("✅ Created client_user_daily_usage table")
        
        # Create client_model_daily_usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_model_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations (id),
                UNIQUE(client_org_id, model_name, usage_date)
            )
        ''')
        print("✅ Created client_model_daily_usage table")
        
        # Create client_billing_summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_billing_summary (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                billing_period TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                profit_margin REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations (id),
                UNIQUE(client_org_id, billing_period)
            )
        ''')
        print("✅ Created client_billing_summary table")
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_mapping_user ON user_client_mapping(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_mapping_client ON user_client_mapping(client_org_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_daily_date ON client_user_daily_usage(usage_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_daily_date ON client_model_daily_usage(usage_date)')
        print("✅ Created performance indexes")
        
        # Commit the changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'client_%' OR name='global_settings' OR name='user_client_mapping'")
        tables = cursor.fetchall()
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 mAI Usage Tracking Migration Tool")
    print("=" * 40)
    
    success = apply_migration()
    
    if success:
        print("\n✅ Next steps:")
        print("1. Run initialize_usage_data.py to set up initial data")
        print("2. Restart your mAI server")
        print("3. Check the Usage tab in Admin Settings")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")