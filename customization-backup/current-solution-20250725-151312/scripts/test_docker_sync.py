#!/usr/bin/env python3
"""
Test script to verify sync function works in Docker environment
"""

import sys
import os

# Add backend path
sys.path.append('/app/backend')

def test_docker_sync():
    """Test sync function in Docker environment"""
    print("🧪 TESTING: Docker Sync Function")
    print("=" * 50)
    
    try:
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        print("✅ Successfully imported openrouter_client_manager")
        
        # Test with a dummy API key
        test_user_id = "55496bfb-252d-43e2-bdf2-6d98d9f88998"  # Your actual user ID
        test_api_key = "sk-or-v1-test123456789abcdef0123456789abcdef0123456789abcdef"
        
        print(f"👤 Test User ID: {test_user_id}")
        print(f"🔑 Test API Key: {test_api_key[:20]}...")
        
        # Call the sync function
        result = openrouter_client_manager.sync_ui_key_to_organization(test_user_id, test_api_key)
        
        print(f"📊 Sync Result: {result}")
        
        if result["success"]:
            print("✅ Sync function works in Docker!")
            print(f"📋 Organization: {result.get('organization_updated')}")
            print(f"💬 Message: {result.get('message')}")
            
            # Restore original API key
            original_key = "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"
            restore_result = openrouter_client_manager.sync_ui_key_to_organization(test_user_id, original_key)
            
            if restore_result["success"]:
                print("✅ Original API key restored")
            
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
    test_docker_sync()