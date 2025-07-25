#!/usr/bin/env python3
"""
Test automatic mapping with a new API key
"""

import sys
import os

# Add backend path
sys.path.append('/app/backend')

def test_new_api_key_mapping():
    """Test sync function with a different API key to verify updates work"""
    print("🧪 TESTING: New API Key Automatic Mapping")
    print("=" * 60)
    
    try:
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        
        # Use the actual Docker user ID
        docker_user_id = "86b5496d-52c8-40f3-a9b1-098560aeb395"
        new_test_key = "sk-or-v1-newtestkey123456789abcdef0123456789abcdef0123456789abcdef"
        
        print(f"👤 Docker User ID: {docker_user_id}")
        print(f"🔑 New Test API Key: {new_test_key[:20]}...")
        
        # This should UPDATE the existing organization, not create a new one
        result = openrouter_client_manager.sync_ui_key_to_organization(docker_user_id, new_test_key)
        
        print(f"📊 Sync Result: {result}")
        
        if result["success"]:
            print("✅ API key update works!")
            print(f"📋 Organization: {result.get('organization_updated')}")
            print(f"💬 Message: {result.get('message')}")
            
            # Verify the update in database
            import sqlite3
            conn = sqlite3.connect('/app/backend/data/webui.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM client_organizations WHERE user_id = ?", (docker_user_id,))
            org_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT name, openrouter_api_key FROM client_organizations ORDER BY updated_at DESC LIMIT 1")
            latest_org = cursor.fetchone()
            
            print(f"📊 Total organizations for user: {org_count}")
            if latest_org:
                print(f"📋 Latest organization: {latest_org[0]}")
                print(f"🔑 Latest API key: {latest_org[1][:20]}...{latest_org[1][-10:]}")
            
            conn.close()
            
            # Restore your original API key
            print("\n🔄 Restoring original API key...")
            original_key = "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"
            restore_result = openrouter_client_manager.sync_ui_key_to_organization(docker_user_id, original_key)
            
            if restore_result["success"]:
                print("✅ Original API key restored")
            else:
                print("⚠️ Could not restore original key")
            
            return True
        else:
            print("❌ API key update failed")
            print(f"💬 Error: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_new_api_key_mapping()