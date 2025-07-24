#!/usr/bin/env python3
"""
Script to set up a test client organization and user mapping for testing usage tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.open_webui.models.organization_usage import (
    GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB,
    GlobalSettingsForm, ClientOrganizationForm, UserClientMappingForm
)

def setup_test_organization():
    """Set up a test organization with a test API key"""
    
    # First, check if global settings exist, if not create them
    settings = GlobalSettingsDB.get_settings()
    if not settings:
        print("Creating global settings...")
        settings_form = GlobalSettingsForm(
            openrouter_provisioning_key=None,  # No provisioning key for test
            default_markup_rate=1.3,
            billing_currency="USD"
        )
        settings = GlobalSettingsDB.create_or_update_settings(settings_form)
        print(f"✓ Global settings created")
    
    # Create a test client organization (without OpenRouter provisioning)
    test_org_form = ClientOrganizationForm(
        name="Test Organization",
        markup_rate=1.3,
        monthly_limit=100.0,
        billing_email="test@example.com"
    )
    
    # Use a dummy API key for testing (in production, this would come from OpenRouter)
    test_api_key = "sk-or-test-" + "x" * 32  # Dummy key format
    
    # Check if test org already exists
    existing_orgs = ClientOrganizationDB.get_all_active_clients()
    test_org = None
    for org in existing_orgs:
        if org.name == "Test Organization":
            test_org = org
            print(f"✓ Test organization already exists: {org.id}")
            break
    
    if not test_org:
        test_org = ClientOrganizationDB.create_client(
            client_form=test_org_form,
            api_key=test_api_key,
            key_hash="test_key_hash"
        )
        print(f"✓ Test organization created: {test_org.id}")
    
    return test_org

def setup_user_mapping(user_id: str, client_org_id: str):
    """Create a mapping between a user and the test organization"""
    
    # Check if mapping already exists
    existing_mapping = UserClientMappingDB.get_mapping_by_user_id(user_id)
    if existing_mapping:
        print(f"✓ User mapping already exists for user {user_id}")
        return existing_mapping
    
    # Create new mapping
    mapping_form = UserClientMappingForm(
        user_id=user_id,
        client_org_id=client_org_id,
        openrouter_user_id=f"openrouter_user_{user_id}"  # Format for OpenRouter tracking
    )
    
    mapping = UserClientMappingDB.create_mapping(mapping_form)
    if mapping:
        print(f"✓ User mapping created: {user_id} -> {client_org_id}")
    else:
        print(f"✗ Failed to create user mapping")
    
    return mapping

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up test client organization and user mapping")
    parser.add_argument("--user-id", help="User ID to map to the test organization", required=True)
    args = parser.parse_args()
    
    print("\n=== Setting up test client organization ===\n")
    
    # Set up test organization
    test_org = setup_test_organization()
    
    if test_org:
        print(f"\nOrganization Details:")
        print(f"  ID: {test_org.id}")
        print(f"  Name: {test_org.name}")
        print(f"  API Key: {test_org.openrouter_api_key[:20]}...")
        print(f"  Markup Rate: {test_org.markup_rate}")
        print(f"  Monthly Limit: ${test_org.monthly_limit}")
        
        # Set up user mapping
        print(f"\n=== Setting up user mapping ===\n")
        mapping = setup_user_mapping(args.user_id, test_org.id)
        
        if mapping:
            print(f"\n✓ Setup complete! User {args.user_id} is now mapped to {test_org.name}")
            print(f"  OpenRouter User ID: {mapping.openrouter_user_id}")
        else:
            print(f"\n✗ Failed to complete setup")
    else:
        print("\n✗ Failed to create test organization")