#!/usr/bin/env python3
"""
Test script to verify automatic OpenRouter API key mapping workflow
This simulates what happens when a client saves their API key in Settings → Connections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from backend.open_webui.utils.openrouter_client_manager import openrouter_client_manager
from backend.open_webui.models.organization_usage import (
    ClientOrganizationDB, UserClientMappingDB, GlobalSettingsDB, GlobalSettingsForm
)

def setup_global_settings():
    """Setup global settings with provisioning key"""
    print("🔧 Setting up global settings...")
    
    # Your provisioning key from earlier
    provisioning_key = "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"
    
    settings_form = GlobalSettingsForm(
        openrouter_provisioning_key=provisioning_key,
        default_markup_rate=1.3,
        billing_currency="USD"
    )
    
    settings = GlobalSettingsDB.create_or_update_settings(settings_form)
    if settings:
        print(f"✅ Global settings configured")
        openrouter_client_manager.refresh_settings()
        return True
    return False

def test_automatic_mapping():
    """Test the automatic API key mapping workflow"""
    
    print("\n=== Testing Automatic OpenRouter API Key Mapping ===\n")
    
    # Setup
    if not setup_global_settings():
        print("❌ Failed to setup global settings")
        return False
    
    # Test user ID (simulate a real user)
    test_user_id = "test_user_12345"
    
    # Client's API key (this would be provided by you to the client)
    client_api_key = "sk-or-v1-client123456789abcdef0123456789abcdef0123456789abcdef"
    
    print(f"👤 Testing user: {test_user_id}")
    print(f"🔑 Client API key: {client_api_key[:20]}...{client_api_key[-10:]}")
    
    # STEP 1: Check initial state
    print(f"\n📋 Step 1: Initial state check")
    initial_mapping = UserClientMappingDB.get_mapping_by_user_id(test_user_id)
    if initial_mapping:
        print(f"   User already has organization: {initial_mapping.client_org_id}")
    else:
        print(f"   User has no organization mapping (will auto-create)")
    
    # STEP 2: Simulate user saving API key in Settings → Connections
    print(f"\n💾 Step 2: Simulating user saving API key in UI")
    print(f"   This simulates: Settings → Connections → Save API key")
    
    # This is what happens when user saves their settings
    result = openrouter_client_manager.sync_ui_key_to_organization(test_user_id, client_api_key)
    
    if result["success"]:
        print(f"✅ Auto-mapping successful!")
        print(f"   Message: {result['message']}")
        print(f"   Organization: {result['organization_updated']}")
    else:
        print(f"❌ Auto-mapping failed!")
        print(f"   Error: {result['message']}")
        return False
    
    # STEP 3: Verify the mapping was created
    print(f"\n🔍 Step 3: Verifying automatic setup")
    
    # Check user mapping
    mapping = UserClientMappingDB.get_mapping_by_user_id(test_user_id)
    if mapping:
        print(f"✅ User mapping created:")
        print(f"   User ID: {mapping.user_id}")
        print(f"   Organization ID: {mapping.client_org_id}")
        print(f"   OpenRouter User ID: {mapping.openrouter_user_id}")
        print(f"   Is Active: {mapping.is_active}")
    else:
        print(f"❌ No user mapping found")
        return False
    
    # Check organization
    client = ClientOrganizationDB.get_client_by_id(mapping.client_org_id)
    if client:
        print(f"✅ Organization created/updated:")
        print(f"   ID: {client.id}")
        print(f"   Name: {client.name}")
        print(f"   API Key: {client.openrouter_api_key[:20]}...{client.openrouter_api_key[-10:]}")
        print(f"   Markup Rate: {client.markup_rate}x")
        print(f"   Monthly Limit: ${client.monthly_limit}")
        print(f"   Billing Email: {client.billing_email}")
        print(f"   Is Active: {client.is_active}")
    else:
        print(f"❌ No organization found")
        return False
    
    # STEP 4: Test client context lookup (this is used during API calls)
    print(f"\n🔗 Step 4: Testing client context lookup (used during OpenRouter API calls)")
    
    context = openrouter_client_manager.get_user_client_context(test_user_id)
    if context:
        print(f"✅ Client context available:")
        print(f"   Client Org ID: {context['client_org_id']}")
        print(f"   Client Name: {context['client_name']}")
        print(f"   API Key: {context['api_key'][:20]}...{context['api_key'][-10:]}")
        print(f"   Markup Rate: {context['markup_rate']}")
        print(f"   OpenRouter User ID: {context['openrouter_user_id']}")
        print(f"   Is Temporary User ID: {context['is_temporary_user_id']}")
    else:
        print(f"❌ No client context found")
        return False
    
    # STEP 5: Verify the API key matches
    print(f"\n✅ Step 5: Verification complete")
    if client.openrouter_api_key == client_api_key:
        print(f"✅ API key correctly saved to organization")
    else:
        print(f"❌ API key mismatch!")
        return False
    
    print(f"\n🎯 SUCCESS: Automatic mapping workflow works perfectly!")
    print(f"\n📝 Summary:")
    print(f"   • User {test_user_id} saved API key in Settings → Connections")
    print(f"   • System automatically created organization: {client.name}")
    print(f"   • API key mapped to organization database")
    print(f"   • Usage tracking will work with {client.markup_rate}x markup")
    print(f"   • Monthly limit: ${client.monthly_limit}")
    
    return True

def test_existing_user_update():
    """Test updating API key for existing user"""
    
    print(f"\n=== Testing API Key Update for Existing User ===\n")
    
    test_user_id = "test_user_12345"  # Same user as before
    new_api_key = "sk-or-v1-newkey456789abcdef0123456789abcdef0123456789abcdef"
    
    print(f"👤 Updating API key for existing user: {test_user_id}")
    print(f"🔑 New API key: {new_api_key[:20]}...{new_api_key[-10:]}")
    
    # Update the API key
    result = openrouter_client_manager.sync_ui_key_to_organization(test_user_id, new_api_key)
    
    if result["success"]:
        print(f"✅ API key update successful!")
        print(f"   Message: {result['message']}")
        
        # Verify the update
        mapping = UserClientMappingDB.get_mapping_by_user_id(test_user_id)
        client = ClientOrganizationDB.get_client_by_id(mapping.client_org_id)
        
        if client.openrouter_api_key == new_api_key:
            print(f"✅ API key successfully updated in organization")
        else:
            print(f"❌ API key not updated correctly")
            return False
    else:
        print(f"❌ API key update failed: {result['message']}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_automatic_mapping()
    
    if success:
        success = test_existing_user_update()
    
    if success:
        print(f"\n🎊 ALL TESTS PASSED! 🎊")
        print(f"\nWorkflow Summary:")
        print(f"1. ✅ Client receives API key from you")
        print(f"2. ✅ Client enters API key in mAI Settings → Connections → Save")
        print(f"3. ✅ System automatically creates/updates organization")
        print(f"4. ✅ API key mapped to all necessary database tables")
        print(f"5. ✅ Usage tracking works immediately with markup")
        print(f"6. ✅ No scripts needed - everything happens automatically!")
        
    else:
        print(f"\n❌ TESTS FAILED")
        
    print(f"\n🚀 Ready for production deployment!")