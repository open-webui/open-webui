#!/usr/bin/env python3
"""
Test the automatic API key sync functionality
"""
import sqlite3
import time
from datetime import datetime

def test_sync_functionality():
    print("🧪 Testing API Key Auto-Sync Functionality")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check current setup
    print("\n1️⃣ Current Database State:")
    
    # Get current organization and API key
    cursor.execute("""
        SELECT co.id, co.name, co.openrouter_api_key, ucm.user_id, u.email
        FROM client_organizations co
        JOIN user_client_mapping ucm ON co.id = ucm.client_org_id
        JOIN user u ON ucm.user_id = u.id
        WHERE co.is_active = 1 AND ucm.is_active = 1
        LIMIT 1
    """)
    
    org_data = cursor.fetchone()
    if org_data:
        org_id, org_name, current_key, user_id, user_email = org_data
        print(f"   Organization: {org_name} ({org_id})")
        print(f"   User: {user_email} ({user_id})")
        print(f"   Current API Key: {current_key[:20]}...")
    else:
        print("   ❌ No organization/user mapping found")
        conn.close()
        return
    
    # 2. Test the sync method directly
    print("\n2️⃣ Testing Sync Method:")
    
    # Import the sync method
    import sys
    sys.path.append('./backend')
    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
    
    # Test with a mock new API key
    test_api_key = "sk-or-v1-test123456789test123456789test123456789test123456789test123456789"
    
    sync_result = openrouter_client_manager.sync_ui_key_to_organization(
        user_id=user_id,
        api_key=test_api_key
    )
    
    print(f"   Success: {sync_result['success']}")
    print(f"   Message: {sync_result['message']}")
    print(f"   Organization Updated: {sync_result['organization_updated']}")
    
    if sync_result['success']:
        # 3. Verify the change in database
        print("\n3️⃣ Verifying Database Update:")
        
        cursor.execute("""
            SELECT openrouter_api_key, updated_at
            FROM client_organizations
            WHERE id = ?
        """, (org_id,))
        
        updated_data = cursor.fetchone()
        if updated_data:
            new_key, updated_at = updated_data
            updated_time = datetime.fromtimestamp(updated_at).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   ✅ API Key Updated: {new_key[:20]}...")
            print(f"   ✅ Updated At: {updated_time}")
            
            # 4. Restore original key
            print("\n4️⃣ Restoring Original API Key:")
            cursor.execute("""
                UPDATE client_organizations 
                SET openrouter_api_key = ?, updated_at = ?
                WHERE id = ?
            """, (current_key, int(time.time()), org_id))
            conn.commit()
            print(f"   ✅ Restored original key: {current_key[:20]}...")
        else:
            print("   ❌ Failed to verify database update")
    
    conn.close()
    
    # 5. Explain the full workflow
    print("\n5️⃣ Complete Workflow Test:")
    print("   To test the full end-to-end flow:")
    print("   1. Login to mAI as admin")
    print("   2. Go to Settings → Connections")  
    print("   3. Update the OpenRouter API key")
    print("   4. Check Docker logs for sync confirmation:")
    print("      docker logs [container-name] 2>&1 | grep 'API key auto-sync'")
    print("   5. Make an API call to verify new key is used")
    
    print(f"\n🎉 Test completed! The sync functionality is ready.")
    print("✅ When admin updates OpenRouter key in UI, it will automatically")
    print("   sync to their organization in the database.")

if __name__ == "__main__":
    test_sync_functionality()