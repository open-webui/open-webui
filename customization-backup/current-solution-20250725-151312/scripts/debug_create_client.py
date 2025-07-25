#!/usr/bin/env python3
"""
Debug script to see exactly why create_client fails
"""

import sys
import os
import time

# Add backend path
sys.path.append('/app/backend')

def debug_create_client():
    """Debug create_client failure in detail"""
    print("🔍 DEBUGGING: create_client Failure")
    print("=" * 50)
    
    try:
        from open_webui.models.organization_usage import (
            ClientOrganizationDB, ClientOrganizationForm
        )
        
        # Test parameters
        user_id = "86b5496d-52c8-40f3-a9b1-098560aeb395"
        api_key = "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"
        org_name = "client_default_organization_" + str(int(time.time()))
        
        print(f"👤 User ID: {user_id}")
        print(f"🔑 API Key: {api_key[:20]}...")
        print(f"🏢 Org Name: {org_name}")
        
        # Create the form
        client_form = ClientOrganizationForm(
            name=org_name,
            markup_rate=1.3,
            monthly_limit=1000.0,
            billing_email=f"billing+{user_id[:8]}@client.local"
        )
        
        print(f"📋 Client Form: {client_form}")
        
        # Try to create the client
        print("\n🔄 Attempting to create client...")
        client = ClientOrganizationDB.create_client(
            client_form=client_form,
            api_key=api_key,
            key_hash=None
        )
        
        if client:
            print(f"✅ Client created successfully!")
            print(f"   ID: {client.id}")
            print(f"   Name: {client.name}")
            print(f"   API Key: {client.openrouter_api_key[:20]}...")
            return True
        else:
            print("❌ Client creation returned None")
            
            # Let's try to create it manually to see the exact error
            print("\n🔍 Trying manual creation to see error...")
            from open_webui.internal.db import get_db
            from open_webui.models.organization_usage import ClientOrganization
            
            try:
                with get_db() as db:
                    current_time = int(time.time())
                    client_data = client_form.model_dump()
                    client_data.update({
                        "id": f"client_{client_form.name.lower().replace(' ', '_')}_{current_time}",
                        "openrouter_api_key": api_key,
                        "openrouter_key_hash": None,
                        "is_active": 1,
                        "created_at": current_time,
                        "updated_at": current_time
                    })
                    
                    print(f"📊 Client data: {client_data}")
                    
                    new_client = ClientOrganization(**client_data)
                    db.add(new_client)
                    db.commit()
                    print("✅ Manual creation worked!")
                    return True
                    
            except Exception as manual_error:
                print(f"❌ Manual creation failed: {manual_error}")
                print(f"   Error type: {type(manual_error)}")
                
                # Check if tables exist
                print("\n📊 Checking database tables...")
                import sqlite3
                conn = sqlite3.connect('/app/backend/data/webui.db')
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%organization%';")
                tables = cursor.fetchall()
                print(f"Organization tables: {tables}")
                conn.close()
                
                return False
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_create_client()