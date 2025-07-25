#!/usr/bin/env python3
"""
Debug and fix the API key mapping issue for Org_C
"""

import sqlite3
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# The API key that should have been mapped
TARGET_API_KEY = "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"
ORG_NAME = "Org_C"

def debug_mapping_issue():
    """Debug why the API key mapping failed"""
    print("🔍 DEBUG: API Key Mapping Issue")
    print("=" * 50)
    print(f"Target API Key: {TARGET_API_KEY}")
    print(f"Organization Name: {ORG_NAME}")
    print()
    
    # Check database connection
    try:
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Check if API key exists anywhere
    cursor.execute("SELECT * FROM client_organizations WHERE openrouter_api_key = ?", (TARGET_API_KEY,))
    existing_org = cursor.fetchone()
    
    if existing_org:
        print(f"✅ API key found in database: {existing_org}")
        conn.close()
        return
    else:
        print("❌ API key NOT found in database")
    
    # Check if organization name exists
    cursor.execute("SELECT * FROM client_organizations WHERE name = ?", (ORG_NAME,))
    org_by_name = cursor.fetchone()
    
    if org_by_name:
        print(f"⚠️ Organization name exists with different API key: {org_by_name}")
    else:
        print("❌ Organization name NOT found")
    
    # Check current user settings to see if they have OpenRouter configured
    cursor.execute("SELECT id, email FROM user")
    users = cursor.fetchall()
    
    print(f"\n👥 Users in system: {len(users)}")
    for user in users:
        print(f"  - {user[1]} (ID: {user[0]})")
    
    # Check current organizations
    cursor.execute("SELECT * FROM client_organizations ORDER BY created_at DESC")
    orgs = cursor.fetchall()
    
    print(f"\n🏢 Organizations in system: {len(orgs)}")
    for org in orgs[:3]:  # Show first 3
        print(f"  - {org[1]} | Key: {org[2][:20]}...{org[2][-10:] if len(org[2]) > 30 else org[2]}")
    
    conn.close()
    
    print("\n🔧 SOLUTION:")
    print("1. The automatic mapping failed - API key was not detected")
    print("2. This could be because:")
    print("   - User didn't save the settings properly")
    print("   - The sync function had an error")
    print("   - The API key format validation failed")
    print("   - Database permissions issue")
    print("\n3. To fix this, we can manually create the organization mapping")
    
    return True

def manual_fix_mapping():
    """Manually create the missing organization mapping"""
    print("\n🛠️ MANUAL FIX: Creating Organization Mapping")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        
        # Get the user ID (assuming there's only one user)
        cursor.execute("SELECT id, email FROM user LIMIT 1")
        user = cursor.fetchone()
        
        if not user:
            print("❌ No user found in system")
            return False
        
        user_id, user_email = user
        print(f"👤 User: {user_email} (ID: {user_id})")
        
        # Create the organization
        org_id = f"client_{ORG_NAME.lower().replace(' ', '_').replace('_', '')}_{int(datetime.now().timestamp())}"
        current_time = int(datetime.now().timestamp())
        
        # Insert organization
        cursor.execute("""
            INSERT INTO client_organizations 
            (id, name, openrouter_api_key, openrouter_key_hash, markup_rate, monthly_limit, billing_email, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            org_id,
            ORG_NAME,
            TARGET_API_KEY,
            "manual_hash",
            1.3,
            1000.0,
            f"admin@{ORG_NAME.lower().replace(' ', '')}.com",
            1,
            current_time,
            current_time
        ))
        
        print(f"✅ Created organization: {org_id}")
        
        # Create user mapping
        mapping_id = f"{user_id}_{org_id}"
        openrouter_user_id = f"temp_{user_id}_{current_time}"
        
        cursor.execute("""
            INSERT INTO user_client_mapping 
            (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping_id,
            user_id,
            org_id,
            openrouter_user_id,
            1,
            current_time,
            current_time
        ))
        
        print(f"✅ Created user mapping: {mapping_id}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n🎉 SUCCESS: Organization and user mapping created!")
        print(f"📋 Organization ID: {org_id}")
        print(f"🔑 API Key: {TARGET_API_KEY}")
        print(f"👤 User: {user_email}")
        print(f"🆔 OpenRouter User ID: {openrouter_user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create mapping: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_mapping():
    """Verify the mapping was created correctly"""
    print("\n✅ VERIFICATION: Checking Created Mapping")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        
        # Check organization
        cursor.execute("SELECT * FROM client_organizations WHERE openrouter_api_key = ?", (TARGET_API_KEY,))
        org = cursor.fetchone()
        
        if org:
            print(f"✅ Organization found: {org[1]} (ID: {org[0]})")
            
            # Check user mapping
            cursor.execute("SELECT * FROM user_client_mapping WHERE client_org_id = ?", (org[0],))
            mappings = cursor.fetchall()
            
            print(f"✅ User mappings: {len(mappings)}")
            for mapping in mappings:
                print(f"  - User {mapping[1]} → Org {mapping[2]} (OpenRouter: {mapping[3]})")
            
        else:
            print("❌ Organization still not found")
        
        conn.close()
        return org is not None
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    print("🚨 API KEY MAPPING DEBUG & FIX TOOL")
    print("=" * 60)
    
    # Step 1: Debug the issue
    debug_mapping_issue()
    
    # Step 2: Ask if user wants to fix it
    response = input("\n❓ Do you want to manually create the missing mapping? (y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        # Step 3: Fix the mapping
        if manual_fix_mapping():
            # Step 4: Verify it worked
            verify_mapping()
            print("\n✨ The API key should now be properly mapped in the system!")
        else:
            print("\n❌ Failed to fix the mapping issue")
    else:
        print("\n⚠️ Mapping issue not fixed. Manual intervention required.")

if __name__ == "__main__":
    main()