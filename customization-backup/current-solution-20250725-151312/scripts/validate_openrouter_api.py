#!/usr/bin/env python3
"""
Validation script for OpenRouter Provisioning API
Tests the API key generation against real OpenRouter endpoints
"""

import sys
import os
import asyncio
import requests
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Your Org_B Provisioning Key
PROVISIONING_KEY = "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"

def test_provisioning_key_direct():
    """Test the provisioning key directly against OpenRouter API"""
    print("🔍 Testing Provisioning Key directly with OpenRouter API...")
    
    headers = {
        "Authorization": f"Bearer {PROVISIONING_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test 1: List existing keys
    print("\n📋 Test 1: List existing API keys")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/keys",
            headers=headers,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully listed keys")
            if "data" in data:
                print(f"   Found {len(data['data'])} existing keys")
            else:
                print(f"   Response structure: {list(data.keys())}")
        else:
            print(f"❌ Failed to list keys: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error listing keys: {e}")
    
    # Test 2: Create a test API key
    print(f"\n🔑 Test 2: Create test API key")
    try:
        create_data = {
            "name": "Test Client Key",
            "label": "test-validation-key",
            "limit": 10.0  # Small limit for testing
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/keys/",
            headers=headers,
            json=create_data,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Request data: {create_data}")
        print(f"   Response: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Successfully created API key")
            
            # Look for the actual API key in the response
            if "data" in data:
                key_data = data["data"]
                print(f"   Response data keys: {list(key_data.keys())}")
                
                # Look for the API key field
                api_key = None
                for field_name, field_value in key_data.items():
                    if isinstance(field_value, str) and field_value.startswith("sk-or-"):
                        api_key = field_value
                        print(f"   Found API key in field '{field_name}': {api_key[:20]}...{api_key[-10:]}")
                        break
                
                if not api_key:
                    print(f"   ⚠️ No API key found in response")
                
                # Get the key hash for cleanup
                key_hash = key_data.get("hash")
                if key_hash:
                    print(f"   Key hash: {key_hash}")
                    
                    # Test 3: Clean up the test key
                    print(f"\n🗑️ Test 3: Delete test key")
                    try:
                        delete_response = requests.delete(
                            f"https://openrouter.ai/api/v1/keys/{key_hash}",
                            headers=headers,
                            timeout=30
                        )
                        
                        print(f"   Delete status: {delete_response.status_code}")
                        if delete_response.status_code in [200, 204]:
                            print(f"✅ Test key deleted successfully")
                        else:
                            print(f"⚠️ Failed to delete test key: {delete_response.text}")
                            
                    except Exception as e:
                        print(f"❌ Error deleting test key: {e}")
            else:
                print(f"   Unexpected response structure: {list(data.keys())}")
                
        else:
            print(f"❌ Failed to create API key")
            
    except Exception as e:
        print(f"❌ Error creating test key: {e}")

async def test_with_client_manager():
    """Test using our OpenRouter client manager"""
    print(f"\n🔧 Testing with OpenRouter Client Manager...")
    
    from backend.open_webui.models.organization_usage import GlobalSettingsDB, GlobalSettingsForm
    from backend.open_webui.utils.openrouter_client_manager import openrouter_client_manager
    
    # Setup provisioning key
    print("   Setting up provisioning key...")
    settings_form = GlobalSettingsForm(
        openrouter_provisioning_key=PROVISIONING_KEY,
        default_markup_rate=1.3,
        billing_currency="USD"
    )
    
    settings = GlobalSettingsDB.create_or_update_settings(settings_form)
    if settings:
        openrouter_client_manager.refresh_settings()
        print("✅ Provisioning key configured")
    else:
        print("❌ Failed to configure provisioning key")
        return
    
    # Test API key creation
    print("   Creating test API key...")
    result = await openrouter_client_manager.create_client_api_key(
        client_name="Validation Test Client",
        credit_limit=5.0
    )
    
    if result:
        print("✅ Client manager API key creation successful")
        print(f"   Result keys: {list(result.keys())}")
        
        if "key" in result:
            api_key = result["key"]
            print(f"   Generated API key: {api_key[:20]}...{api_key[-10:]}")
        else:
            print(f"   No 'key' field in result")
            
        if "hash" in result:
            key_hash = result["hash"]
            print(f"   Key hash: {key_hash}")
            
            # Clean up
            try:
                deleted = await openrouter_client_manager.delete_api_key(key_hash)
                if deleted:
                    print("✅ Test key cleaned up")
                else:
                    print("⚠️ Failed to clean up test key")
            except Exception as e:
                print(f"⚠️ Error cleaning up: {e}")
    else:
        print("❌ Client manager API key creation failed")

def main():
    print("=" * 60)
    print("🔍 OPENROUTER PROVISIONING API VALIDATION")
    print("=" * 60)
    print(f"Provisioning Key: {PROVISIONING_KEY[:20]}...{PROVISIONING_KEY[-10:]}")
    
    # Test direct API calls
    test_provisioning_key_direct()
    
    # Test with our client manager
    asyncio.run(test_with_client_manager())
    
    print(f"\n" + "=" * 60)
    print("✅ VALIDATION COMPLETE")
    print("If all tests passed, your script should work correctly!")
    print("=" * 60)

if __name__ == "__main__":
    main()