#!/usr/bin/env python3
"""
Debug script to find why usage isn't showing in the Usage tab
"""

import sqlite3
import json
from datetime import date, datetime

def check_database():
    """Check database tables and content"""
    print("🔍 STEP 1: Checking Database Tables and Content")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check if tables exist
    print("\n📊 Checking usage tracking tables:")
    tables_to_check = [
        'client_organizations',
        'user_client_mapping', 
        'client_live_counters',
        'client_daily_usage',
        'client_user_daily_usage',
        'client_model_daily_usage'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables_to_check:
        if table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} records")
            
            # Show sample data
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchone()
                print(f"   Sample: {dict(zip(columns, data))}")
        else:
            print(f"❌ {table}: MISSING!")
    
    # 2. Check user information
    print("\n👤 Checking user data:")
    cursor.execute("SELECT id, email, role FROM user WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    if admin:
        print(f"Admin user: {admin[1]} (ID: {admin[0]})")
        
        # Check if admin has organization mapping
        cursor.execute("SELECT * FROM user_client_mapping WHERE user_id = ?", (admin[0],))
        mapping = cursor.fetchone()
        if mapping:
            print(f"✅ Admin is mapped to organization: {mapping[2]}")
        else:
            print(f"❌ Admin has NO organization mapping!")
    
    # 3. Check today's usage
    print("\n📈 Checking today's usage data:")
    today = date.today().isoformat()
    
    # Check live counters
    cursor.execute("SELECT * FROM client_live_counters WHERE current_date = ?", (today,))
    live_data = cursor.fetchall()
    if live_data:
        print(f"✅ Live counters for today: {len(live_data)} records")
        for row in live_data:
            print(f"   Client: {row[0]}, Tokens: {row[2]}, Requests: {row[3]}, Cost: ${row[5]:.6f}")
    else:
        print("❌ No live counter data for today!")
    
    # Check daily usage
    cursor.execute("SELECT * FROM client_daily_usage WHERE usage_date = ?", (today,))
    daily_data = cursor.fetchall()
    if daily_data:
        print(f"✅ Daily usage for today: {len(daily_data)} records")
    else:
        print("⚠️  No daily usage records for today (this is normal if using live counters)")
    
    conn.close()
    return admin[0] if admin else None

def check_api_response(admin_user_id):
    """Simulate what the API would return"""
    print("\n🌐 STEP 2: Simulating API Response")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get user's organization
    cursor.execute("""
        SELECT ucm.client_org_id, co.name 
        FROM user_client_mapping ucm
        JOIN client_organizations co ON ucm.client_org_id = co.id
        WHERE ucm.user_id = ? AND ucm.is_active = 1
    """, (admin_user_id,))
    
    org_data = cursor.fetchone()
    if not org_data:
        print("❌ No organization found for user!")
        return
    
    client_org_id, org_name = org_data
    print(f"✅ User organization: {org_name} ({client_org_id})")
    
    # Check what the API would return
    today = date.today()
    
    # Get live counter data
    cursor.execute("""
        SELECT today_tokens, today_requests, today_raw_cost, today_markup_cost, last_updated
        FROM client_live_counters 
        WHERE client_org_id = ? AND current_date = ?
    """, (client_org_id, today.isoformat()))
    
    live_data = cursor.fetchone()
    if live_data:
        print(f"\n📊 Today's Live Data:")
        print(f"   Tokens: {live_data[0]}")
        print(f"   Requests: {live_data[1]}")
        print(f"   Raw Cost: ${live_data[2]:.6f}")
        print(f"   Markup Cost: ${live_data[3]:.6f}")
        print(f"   Last Updated: {datetime.fromtimestamp(live_data[4]).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n❌ No live data found for today!")
    
    # Get historical data
    cursor.execute("""
        SELECT usage_date, total_tokens, total_requests, markup_cost
        FROM client_daily_usage
        WHERE client_org_id = ?
        ORDER BY usage_date DESC
        LIMIT 5
    """, (client_org_id,))
    
    historical = cursor.fetchall()
    if historical:
        print(f"\n📅 Historical Data (last 5 days):")
        for row in historical:
            print(f"   {row[0]}: {row[1]} tokens, {row[2]} requests, ${row[3]:.6f}")
    
    conn.close()

def check_recording_setup():
    """Check if usage recording is properly configured"""
    print("\n🔧 STEP 3: Checking Usage Recording Configuration")
    print("=" * 60)
    
    # Check if OpenRouter integration is set up
    print("\n🔍 Key files to check:")
    
    files_to_check = [
        ("backend/open_webui/routers/openai.py", "record_real_time_usage", "Usage recording integration"),
        ("backend/open_webui/utils/openrouter_client_manager.py", "record_real_time_usage", "Recording function"),
        ("backend/open_webui/models/organization_usage.py", "record_usage", "Database recording"),
        ("backend/open_webui/routers/client_organizations.py", "/usage/my-organization", "API endpoint")
    ]
    
    import os
    for file_path, search_term, description in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                if search_term in content:
                    print(f"✅ {description}: Found in {file_path}")
                else:
                    print(f"❌ {description}: NOT FOUND in {file_path}")
        else:
            print(f"❌ File not found: {file_path}")

def suggest_fixes():
    """Suggest fixes based on findings"""
    print("\n💡 STEP 4: Suggested Fixes")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check common issues
    issues_found = []
    
    # Issue 1: No organization
    cursor.execute("SELECT COUNT(*) FROM client_organizations WHERE is_active = 1")
    if cursor.fetchone()[0] == 0:
        issues_found.append({
            "issue": "No active client organizations",
            "fix": "Run: python3 setup_client_org.py"
        })
    
    # Issue 2: No user mapping
    cursor.execute("SELECT COUNT(*) FROM user_client_mapping WHERE is_active = 1")
    if cursor.fetchone()[0] == 0:
        issues_found.append({
            "issue": "No user-organization mappings",
            "fix": "Create mapping for admin user"
        })
    
    # Issue 3: No usage data
    cursor.execute("SELECT COUNT(*) FROM client_live_counters")
    live_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM client_daily_usage")
    daily_count = cursor.fetchone()[0]
    
    if live_count == 0 and daily_count == 0:
        issues_found.append({
            "issue": "No usage data recorded",
            "fix": "Check if OpenRouter integration is working in openai.py"
        })
    
    if issues_found:
        print("\n🚨 Issues Found:")
        for idx, issue in enumerate(issues_found, 1):
            print(f"\n{idx}. {issue['issue']}")
            print(f"   Fix: {issue['fix']}")
    else:
        print("\n✅ Basic setup looks correct!")
        print("\n🔍 Additional debugging steps:")
        print("1. Check browser console for JavaScript errors")
        print("2. Check network tab for API responses")
        print("3. Add debug logging to openai.py around line 956")
        print("4. Verify OpenRouter is returning usage data in response")
    
    conn.close()

def create_test_mapping():
    """Create a test user-organization mapping if needed"""
    print("\n🔧 STEP 5: Creating Test Mapping (if needed)")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get admin user
    cursor.execute("SELECT id FROM user WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    if not admin:
        print("❌ No admin user found!")
        return
    
    admin_id = admin[0]
    
    # Check if mapping exists
    cursor.execute("SELECT * FROM user_client_mapping WHERE user_id = ?", (admin_id,))
    if cursor.fetchone():
        print("✅ User mapping already exists")
        return
    
    # Get or create organization
    cursor.execute("SELECT id FROM client_organizations WHERE is_active = 1 LIMIT 1")
    org = cursor.fetchone()
    
    if not org:
        # Create default organization
        import time
        org_id = f"client_default_{int(time.time())}"
        cursor.execute("""
            INSERT INTO client_organizations 
            (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (org_id, "Default Organization", "sk-or-placeholder", 1.3, 1, int(time.time()), int(time.time())))
        print(f"✅ Created default organization: {org_id}")
    else:
        org_id = org[0]
        print(f"✅ Using existing organization: {org_id}")
    
    # Create mapping
    import time
    cursor.execute("""
        INSERT INTO user_client_mapping
        (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        f"{admin_id}_{org_id}",
        admin_id,
        org_id,
        f"openrouter_{admin_id}",
        1,
        int(time.time()),
        int(time.time())
    ))
    
    conn.commit()
    print(f"✅ Created user-organization mapping!")
    conn.close()

def main():
    print("🚀 Usage Tracking Debug Script")
    print("=" * 60)
    
    # Step 1: Check database
    admin_user_id = check_database()
    
    if admin_user_id:
        # Step 2: Check API response
        check_api_response(admin_user_id)
    
    # Step 3: Check recording setup
    check_recording_setup()
    
    # Step 4: Suggest fixes
    suggest_fixes()
    
    # Step 5: Offer to create test mapping
    if admin_user_id:
        response = input("\n❓ Create/fix user-organization mapping? (y/n): ")
        if response.lower() == 'y':
            create_test_mapping()
    
    print("\n" + "=" * 60)
    print("✅ Debug complete! Check the findings above.")
    print("\n📋 Next steps:")
    print("1. Fix any issues identified above")
    print("2. Make a new API call through the chat")
    print("3. Check the Usage tab again")
    print("4. If still not working, check browser console and network tab")

if __name__ == "__main__":
    main()