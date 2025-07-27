#!/usr/bin/env python3
"""
Debug client organization lookup in get_environment_client_org_id()
"""

import sqlite3
import os
import hashlib

def debug_client_organization_lookup():
    """Debug the client organization lookup process step by step"""
    print("🔍 Debugging Client Organization Lookup")
    print("=" * 60)
    
    database_path = "backend/data/webui.db"
    
    # Step 1: Check database connection
    print("1. Database Connection Check:")
    if not os.path.exists(database_path):
        print(f"   ❌ Database not found: {database_path}")
        return False
    print(f"   ✅ Database found: {database_path}")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Step 2: Check client_organizations table exists
        print("\n2. Table Structure Check:")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='client_organizations'
        """)
        
        if not cursor.fetchone():
            print("   ❌ client_organizations table not found")
            return False
        print("   ✅ client_organizations table exists")
        
        # Step 3: Check all client organizations
        print("\n3. All Client Organizations:")
        cursor.execute("""
            SELECT id, name, is_active, created_at 
            FROM client_organizations 
            ORDER BY created_at DESC
        """)
        
        all_orgs = cursor.fetchall()
        if not all_orgs:
            print("   ❌ No client organizations found")
            return False
        
        for org in all_orgs:
            org_id, name, is_active, created_at = org
            status = "✅ ACTIVE" if is_active else "❌ INACTIVE"
            print(f"   {status} {org_id} | {name} | Created: {created_at}")
        
        # Step 4: Check active client organizations (what get_all_active_clients() should return)
        print("\n4. Active Client Organizations:")
        cursor.execute("""
            SELECT id, name, is_active 
            FROM client_organizations 
            WHERE is_active = 1
        """)
        
        active_orgs = cursor.fetchall()
        if not active_orgs:
            print("   ❌ No active client organizations found")
            print("   🔧 This is why get_environment_client_org_id() fails!")
            
            # Check if there are inactive ones
            cursor.execute("""
                SELECT COUNT(*) FROM client_organizations WHERE is_active = 0
            """)
            inactive_count = cursor.fetchone()[0]
            if inactive_count > 0:
                print(f"   ⚠️  Found {inactive_count} inactive client organizations")
                print("   💡 Solution: Activate the client organization")
        else:
            print(f"   ✅ Found {len(active_orgs)} active client organizations:")
            for org in active_orgs:
                org_id, name, is_active = org
                print(f"      📋 {org_id} | {name}")
        
        # Step 5: Simulate get_environment_client_org_id logic
        print("\n5. Simulating get_environment_client_org_id() Logic:")
        
        # First part: Check active clients
        if active_orgs:
            first_active_id = active_orgs[0][0]
            print(f"   ✅ Would return first active client: {first_active_id}")
            return_value = first_active_id
        else:
            print("   ⚠️  No active clients found, checking fallback logic...")
            
            # Check ORGANIZATION_NAME environment variable
            org_name = os.getenv('ORGANIZATION_NAME')
            if org_name:
                org_hash = hashlib.md5(org_name.encode()).hexdigest()[:8]
                fallback_id = f"env_client_{org_hash}"
                print(f"   📝 ORGANIZATION_NAME found: {org_name}")
                print(f"   🔄 Would generate fallback ID: {fallback_id}")
                return_value = fallback_id
            else:
                print("   ❌ No ORGANIZATION_NAME environment variable")
                print("   🔄 Would return default: env_client_default")
                return_value = "env_client_default"
        
        # Step 6: Verify if the returned ID has actual usage data
        print(f"\n6. Usage Data Check for '{return_value}':")
        
        # Check user usage
        cursor.execute("""
            SELECT COUNT(*) FROM client_user_daily_usage 
            WHERE client_org_id = ?
        """, (return_value,))
        user_usage_count = cursor.fetchone()[0]
        
        # Check model usage  
        cursor.execute("""
            SELECT COUNT(*) FROM client_model_daily_usage 
            WHERE client_org_id = ?
        """, (return_value,))
        model_usage_count = cursor.fetchone()[0]
        
        print(f"   👥 User usage records: {user_usage_count}")
        print(f"   🤖 Model usage records: {model_usage_count}")
        
        if user_usage_count == 0 and model_usage_count == 0:
            print("   ⚠️  No usage data found for this client organization ID")
            print("   💡 This explains why the tabs show empty data")
            
            # Check if data exists under different client org ID
            cursor.execute("""
                SELECT DISTINCT client_org_id, COUNT(*) as records
                FROM client_user_daily_usage 
                GROUP BY client_org_id
            """)
            user_data_by_org = cursor.fetchall()
            
            cursor.execute("""
                SELECT DISTINCT client_org_id, COUNT(*) as records  
                FROM client_model_daily_usage
                GROUP BY client_org_id
            """)
            model_data_by_org = cursor.fetchall()
            
            if user_data_by_org or model_data_by_org:
                print("\n   📊 Usage data found under different client org IDs:")
                for org_id, count in user_data_by_org:
                    print(f"      👥 {org_id}: {count} user records")
                for org_id, count in model_data_by_org:
                    print(f"      🤖 {org_id}: {count} model records")
        else:
            print("   ✅ Usage data found! Tabs should show data.")
        
        conn.close()
        
        # Step 7: Diagnosis and solution
        print(f"\n🏥 DIAGNOSIS:")
        if not active_orgs:
            print("   ❌ PROBLEM: No active client organizations found")
            print("   🔧 SOLUTION: Activate existing client organization")
        elif user_usage_count == 0 and model_usage_count == 0:
            print("   ❌ PROBLEM: Client org lookup works but no usage data under that ID")
            print("   🔧 SOLUTION: Check usage data organization ID mapping")
        else:
            print("   ✅ CLIENT ORG LOOKUP SHOULD WORK")
            print("   💡 Issue might be elsewhere (API endpoints, frontend, etc.)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

def check_environment_variables():
    """Check relevant environment variables"""
    print(f"\n🌍 Environment Variables Check:")
    print("-" * 40)
    
    env_vars = [
        'ORGANIZATION_NAME',
        'OPENROUTER_EXTERNAL_USER', 
        'OPENROUTER_API_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'API_KEY' in var:
                print(f"   ✅ {var}: {value[:20]}... (hidden)")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: Not set")

def suggest_fix():
    """Suggest production-ready fix based on findings"""
    print(f"\n🔧 PRODUCTION-READY SOLUTION:")
    print("=" * 60)
    print("Based on the diagnosis, the most likely fixes are:")
    print()
    print("1. **Activate Client Organization** (if inactive):")
    print("   ```sql")
    print("   UPDATE client_organizations ")
    print("   SET is_active = 1, updated_at = datetime('now')")
    print("   WHERE id LIKE 'mai_client_%';")
    print("   ```")
    print()
    print("2. **Fix Client Organization ID Mismatch** (if data exists under different ID):")
    print("   - Run the updated generate_client_env.py with --production flag")
    print("   - This will ensure consistent organization ID mapping")
    print()
    print("3. **Environment-Based Setup** (if no client org found):")
    print("   - Ensure ORGANIZATION_NAME environment variable is set")
    print("   - Run generate_client_env.py --production to create missing records")
    print()
    print("4. **Docker Restart** (after database fixes):")  
    print("   ```bash")
    print("   docker-compose down && docker-compose up -d")
    print("   ```")

if __name__ == "__main__":
    print("🐞 Client Organization Lookup Debug Tool")
    print("=" * 60)
    
    success = debug_client_organization_lookup()
    check_environment_variables()
    
    if success:
        suggest_fix()
        print(f"\n✅ Debug completed! Check the diagnosis above for the solution.")
    else:
        print(f"\n❌ Debug failed! Check database connection and schema.")