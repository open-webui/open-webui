#!/usr/bin/env python3
"""
Test sync function with correct Docker user ID
"""

import sys
import os

# Add backend path
sys.path.append('/app/backend')

def test_docker_sync_correct():
    """Test sync function with correct user ID from Docker database"""
    print("🧪 TESTING: Docker Sync with Correct User ID")
    print("=" * 60)
    
    try:
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        print("✅ Successfully imported openrouter_client_manager")
        
        # Use the actual Docker user ID
        docker_user_id = "86b5496d-52c8-40f3-a9b1-098560aeb395"
        test_api_key = "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"
        
        print(f"👤 Docker User ID: {docker_user_id}")
        print(f"🔑 Your actual API Key: {test_api_key[:20]}...")
        
        # Call the sync function
        result = openrouter_client_manager.sync_ui_key_to_organization(docker_user_id, test_api_key)
        
        print(f"📊 Sync Result: {result}")
        
        if result["success"]:
            print("✅ Sync function works in Docker!")
            print(f"📋 Organization: {result.get('organization_updated')}")
            print(f"💬 Message: {result.get('message')}")
            
            # Verify organization was created
            import sqlite3
            conn = sqlite3.connect('/app/backend/data/webui.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM client_organizations WHERE openrouter_api_key = ?", (test_api_key,))
            org = cursor.fetchone()
            
            if org:
                print(f"✅ Organization created: {org[1]} (ID: {org[0]})")
                print(f"🔑 API Key stored: {org[2][:20]}...{org[2][-10:]}")
                
                # Check user mapping
                cursor.execute("SELECT * FROM user_client_mapping WHERE user_id = ?", (docker_user_id,))
                mapping = cursor.fetchone()
                
                if mapping:
                    print(f"✅ User mapping created: {mapping[2]}")
                    print(f"🆔 OpenRouter User ID: {mapping[3]}")
                else:
                    print("❌ User mapping not found")
            else:
                print("❌ Organization not found in database")
            
            conn.close()
            return True
        else:
            print("❌ Sync function failed")
            print(f"💬 Error: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_docker_sync_correct()