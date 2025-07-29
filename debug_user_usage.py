#!/usr/bin/env python3
"""
Debug script for user usage data issues
Manually checks database state and client configuration
"""

import sys
import os
import sqlite3
from datetime import date, datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def check_database_tables():
    """Check if required database tables exist and have data"""
    try:
        from open_webui.config import DATA_DIR
        db_path = f"{DATA_DIR}/webui.db"
        
        print(f"🔍 Checking database at: {db_path}")
        print(f"🔍 Database exists: {os.path.exists(db_path)}")
        
        if not os.path.exists(db_path):
            print("❌ Database file not found!")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if required tables exist
        tables_to_check = [
            'client_organizations',
            'client_daily_usage', 
            'client_user_daily_usage',
            'client_model_daily_usage'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Existing tables: {len(existing_tables)}")
        for table in existing_tables:
            print(f"  - {table}")
            
        print(f"\n🔍 Checking required tables:")
        for table in tables_to_check:
            if table in existing_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count} records")
                
                # Show sample data for user usage table
                if table == 'client_user_daily_usage' and count > 0:
                    cursor.execute(f"SELECT client_org_id, user_id, usage_date, total_tokens, total_requests, markup_cost FROM {table} LIMIT 3")
                    samples = cursor.fetchall()
                    print(f"    Sample records:")
                    for sample in samples:
                        print(f"      client_id={sample[0]}, user_id={sample[1]}, date={sample[2]}, tokens={sample[3]}, requests={sample[4]}, cost=${sample[5]}")
            else:
                print(f"  ❌ {table}: NOT FOUND")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

def check_client_organizations():
    """Check client organization setup"""
    try:
        from open_webui.models.organization_usage import ClientOrganizationDB
        from open_webui.config import ORGANIZATION_NAME
        
        print(f"\n🏢 Organization Configuration:")
        print(f"  ORGANIZATION_NAME: {ORGANIZATION_NAME}")
        
        print(f"\n🔍 Active client organizations:")
        orgs = ClientOrganizationDB.get_all_active_clients()
        if orgs:
            for i, org in enumerate(orgs):
                print(f"  {i+1}. ID: {org.id}")
                print(f"     Name: {org.name}")
                print(f"     Active: {org.is_active}")
                print(f"     Has API Key: {'Yes' if org.openrouter_api_key else 'No'}")
        else:
            print("  ❌ No active client organizations found")
            
    except Exception as e:
        print(f"❌ Client organization check failed: {e}")

def check_client_id_resolution():
    """Check how client ID is resolved"""
    try:
        from open_webui.usage_tracking.repositories.client_repository import ClientRepository
        
        print(f"\n🆔 Client ID Resolution:")
        client_id = ClientRepository.get_environment_client_id()
        print(f"  Resolved client ID: {client_id}")
        
    except Exception as e:
        print(f"❌ Client ID resolution failed: {e}")

def check_users():
    """Check system users"""
    try:
        from open_webui.models.users import Users
        
        print(f"\n👥 System Users:")
        users = Users.get_users()
        print(f"  Total users: {len(users)}")
        
        for i, user in enumerate(users[:5]):  # Show first 5 users
            print(f"  {i+1}. ID: {user.id}")
            print(f"     Name: {user.name}")
            print(f"     Email: {user.email}")
            print(f"     Role: {getattr(user, 'role', 'user')}")
            
        if len(users) > 5:
            print(f"  ... and {len(users) - 5} more users")
            
    except Exception as e:
        print(f"❌ Users check failed: {e}")

def test_user_usage_query():
    """Test the actual user usage query"""
    try:
        from open_webui.usage_tracking.repositories.client_repository import ClientRepository
        from open_webui.models.organization_usage import ClientUsageDB
        
        print(f"\n🔍 Testing User Usage Query:")
        
        # Get client ID
        client_id = ClientRepository.get_environment_client_id()
        print(f"  Using client ID: {client_id}")
        
        if client_id:
            # Query user usage
            usage_data = ClientUsageDB.get_usage_by_user(client_id)
            print(f"  Query result: {len(usage_data)} records")
            
            if usage_data:
                print(f"  Sample results:")
                for i, usage in enumerate(usage_data[:3]):
                    print(f"    {i+1}. User: {usage.get('user_id')}")
                    print(f"       Tokens: {usage.get('total_tokens')}")
                    print(f"       Requests: {usage.get('total_requests')}")
                    print(f"       Cost: ${usage.get('markup_cost')}")
                    print(f"       Days Active: {usage.get('days_active')}")
            else:
                print(f"  ❌ No usage data found for current month")
                
                # Check if there's any historical data
                from datetime import date
                from open_webui.internal.db import get_db
                from open_webui.models.organization_usage.database import ClientUserDailyUsage
                
                with get_db() as db:
                    all_records = db.query(ClientUserDailyUsage).filter(
                        ClientUserDailyUsage.client_org_id == client_id
                    ).all()
                    
                    if all_records:
                        dates = [rec.usage_date for rec in all_records]
                        print(f"  📅 Found {len(all_records)} historical records from {min(dates)} to {max(dates)}")
                    else:
                        print(f"  ❌ No historical usage data found for client {client_id}")
        
    except Exception as e:
        print(f"❌ User usage query test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🐛 mAI User Usage Debug Tool")
    print("=" * 50)
    
    check_database_tables()
    check_client_organizations() 
    check_client_id_resolution()
    check_users()
    test_user_usage_query()
    
    print("\n✅ Debug check complete!")