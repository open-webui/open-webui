#!/usr/bin/env python3
"""
Initialize usage tracking data for existing users.
This script creates default organization and maps existing admin users.
"""

import sqlite3
import time
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, date

def generate_id():
    """Generate a unique ID"""
    return str(uuid.uuid4())

def get_current_timestamp():
    """Get current timestamp in milliseconds"""
    return int(time.time())

def hash_api_key(api_key: str) -> str:
    """Create a hash of the API key for security"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]

def initialize_usage_data():
    """Initialize usage tracking data for existing setup"""
    
    # Connect to the database
    db_path = Path("backend/open_webui/data/webui.db")
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Checking existing setup...")
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_organizations'")
        if not cursor.fetchone():
            print("❌ Usage tracking tables not found. Run apply_usage_migration.py first!")
            return False
        
        # Get admin users
        cursor.execute("""
            SELECT id, name, email, role 
            FROM user 
            WHERE role = 'admin' 
            ORDER BY created_at 
            LIMIT 1
        """)
        admin_user = cursor.fetchone()
        
        if not admin_user:
            print("⚠️  No admin user found. Please create an admin user first.")
            return False
        
        admin_id, admin_name, admin_email, _ = admin_user
        print(f"✅ Found admin user: {admin_name} ({admin_email})")
        
        # Check for existing organization
        cursor.execute("SELECT id, name, openrouter_api_key FROM client_organizations WHERE is_active = 1")
        existing_org = cursor.fetchone()
        
        if existing_org:
            org_id, org_name, api_key = existing_org
            print(f"✅ Found existing organization: {org_name}")
            
            # Check if it has the expected API key from the UI
            # The user mentioned their API key starts with sk-or-v1-0a947aa0
            if not api_key.startswith('sk-or-v1-0a947aa0'):
                print(f"⚠️  Organization has different API key: {api_key[:20]}...")
                print("   This might be why usage isn't showing.")
        else:
            # Create default organization
            print("\n📦 Creating default organization...")
            org_id = f"client_default_organization_{get_current_timestamp()}"
            org_name = "Default Organization"
            timestamp = get_current_timestamp()
            
            # You'll need to update this with the actual API key from Settings
            api_key = "sk-or-v1-YOUR_API_KEY_HERE"  # Placeholder
            
            cursor.execute('''
                INSERT INTO client_organizations 
                (id, name, openrouter_api_key, openrouter_key_hash, markup_rate, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (org_id, org_name, api_key, hash_api_key(api_key), 1.3, 1, timestamp, timestamp))
            
            print(f"✅ Created organization: {org_name}")
            print(f"⚠️  IMPORTANT: Update the API key in the database or through the UI!")
        
        # Check user mapping
        cursor.execute("""
            SELECT um.*, co.name 
            FROM user_client_mapping um
            JOIN client_organizations co ON um.client_org_id = co.id
            WHERE um.user_id = ? AND um.is_active = 1
        """, (admin_id,))
        
        existing_mapping = cursor.fetchone()
        
        if existing_mapping:
            print(f"✅ Admin already mapped to organization")
            
            # Check if they have the correct external_user ID
            external_user_id = existing_mapping[3]  # openrouter_user_id column
            if external_user_id and external_user_id == "openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395":
                print(f"✅ External user ID matches: {external_user_id}")
            else:
                print(f"⚠️  External user ID mismatch or missing: {external_user_id}")
                print("   Expected: openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395")
        else:
            # Create user mapping
            print("\n📦 Creating user-organization mapping...")
            mapping_id = generate_id()
            timestamp = get_current_timestamp()
            
            # Use the external_user from the queries you provided
            external_user_id = "openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395"
            
            cursor.execute('''
                INSERT INTO user_client_mapping 
                (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (mapping_id, admin_id, org_id, external_user_id, 1, timestamp, timestamp))
            
            print(f"✅ Mapped admin to organization with external_user: {external_user_id}")
        
        # Initialize live counters if missing
        cursor.execute("SELECT id FROM client_live_counters WHERE client_org_id = ?", (org_id,))
        if not cursor.fetchone():
            print("\n📦 Initializing live counters...")
            counter_id = generate_id()
            timestamp = get_current_timestamp()
            today = date.today().isoformat()
            
            # Based on your provided data: 939 tokens, 1 request, $0.0003440528
            cursor.execute('''
                INSERT INTO client_live_counters 
                (id, client_org_id, total_tokens, total_requests, raw_cost, markup_cost, last_reset_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (counter_id, org_id, 939, 1, 0.000264656, 0.0003440528, today, timestamp))
            
            print("✅ Initialized live counters with today's usage")
        
        # Add sample daily usage data for testing
        cursor.execute("""
            SELECT COUNT(*) FROM client_user_daily_usage 
            WHERE client_org_id = ? AND usage_date = ?
        """, (org_id, date.today().isoformat()))
        
        if cursor.fetchone()[0] == 0:
            print("\n📦 Adding today's usage data...")
            usage_id = generate_id()
            timestamp = get_current_timestamp()
            
            cursor.execute('''
                INSERT INTO client_user_daily_usage 
                (id, client_org_id, user_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (usage_id, org_id, admin_id, date.today().isoformat(), 939, 1, 0.000264656, 0.0003440528, timestamp, timestamp))
            
            # Also add model usage data
            model_usage_id = generate_id()
            cursor.execute('''
                INSERT INTO client_model_daily_usage 
                (id, client_org_id, model_name, usage_date, total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model_usage_id, org_id, "deepseek/deepseek-chat-v3-0324", date.today().isoformat(), 
                  939, 1, 0.000264656, 0.0003440528, timestamp, timestamp))
            
            print("✅ Added today's usage records")
        
        # Commit all changes
        conn.commit()
        
        print("\n📊 Summary:")
        print(f"Organization: {org_name} (ID: {org_id})")
        print(f"Admin User: {admin_name} (ID: {admin_id})")
        print(f"External User: openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395")
        print(f"Today's Usage: 939 tokens, 1 request, $0.0003440528")
        
        # Important reminders
        print("\n⚠️  IMPORTANT NEXT STEPS:")
        print("1. Update the OpenRouter API key in Settings → Connections")
        print("   Your key should start with: sk-or-v1-0a947aa0...")
        print("2. The system will auto-sync the API key to the database")
        print("3. Restart your mAI server")
        print("4. Check the Usage tab - it should now show data!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 mAI Usage Data Initialization Tool")
    print("=" * 40)
    
    success = initialize_usage_data()
    
    if not success:
        print("\n❌ Initialization failed. Please check the error messages above.")