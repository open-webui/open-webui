#!/usr/bin/env python3
"""
Debug script to understand why sync function fails in Docker
"""

import sys
import os
import sqlite3

# Add backend path
sys.path.append('/app/backend')

def debug_sync_issue():
    """Debug why sync function fails"""
    print("🔍 DEBUGGING: Sync Function Failure")
    print("=" * 50)
    
    try:
        # Check database connectivity
        print("📊 Checking database...")
        conn = sqlite3.connect('/app/backend/data/webui.db')
        cursor = conn.cursor()
        
        # Check user exists
        user_id = "55496bfb-252d-43e2-bdf2-6d98d9f88998"
        cursor.execute("SELECT id, email FROM user WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ User found: {user[1]} (ID: {user[0]})")
        else:
            print("❌ User not found in Docker database")
            return False
        
        # Check user mapping
        cursor.execute("SELECT client_org_id FROM user_client_mapping WHERE user_id = ?", (user_id,))
        mapping = cursor.fetchone()
        
        if mapping:
            print(f"✅ User mapping exists: org_id = {mapping[0]}")
            
            # Check organization
            cursor.execute("SELECT * FROM client_organizations WHERE id = ?", (mapping[0],))
            org = cursor.fetchone()
            
            if org:
                print(f"✅ Organization exists: {org[1]}")
                print(f"🔑 Current API key: {org[2][:20]}...{org[2][-10:]}")
            else:
                print("❌ Organization not found")
                return False
        else:
            print("❌ No user mapping found - should create default organization")
        
        conn.close()
        
        # Now test the sync function step by step
        print("\n🔄 Testing sync function...")
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        
        # Check if user already has mapping (should take existing org path)
        from open_webui.models.organization_usage import UserClientMappingDB, ClientOrganizationDB
        
        existing_mapping = UserClientMappingDB.get_mapping_by_user_id(user_id)
        if existing_mapping:
            print(f"✅ Found existing mapping: {existing_mapping.client_org_id}")
            
            # Check if organization exists
            existing_org = ClientOrganizationDB.get_client_by_id(existing_mapping.client_org_id)
            if existing_org:
                print(f"✅ Organization exists, should UPDATE API key")
                print(f"   Current: {existing_org.openrouter_api_key[:20]}...")
                
                # This should be the UPDATE path, not CREATE path
                test_key = "sk-or-v1-test123456789abcdef0123456789abcdef0123456789abcdef"
                
                # Try the update directly
                updates = {
                    "openrouter_api_key": test_key,
                    "updated_at": int(__import__('time').time())
                }
                
                updated_client = ClientOrganizationDB.update_client(existing_mapping.client_org_id, updates)
                if updated_client:
                    print("✅ Direct update works!")
                    
                    # Restore original key
                    original_key = "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"
                    restore_updates = {
                        "openrouter_api_key": original_key,
                        "updated_at": int(__import__('time').time())
                    }
                    ClientOrganizationDB.update_client(existing_mapping.client_org_id, restore_updates)
                    print("✅ Original key restored")
                    
                    return True
                else:
                    print("❌ Direct update failed")
                    return False
            else:
                print("❌ Organization not found, this is the issue!")
                return False
        else:
            print("❌ No existing mapping found")
            return False
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_sync_issue()