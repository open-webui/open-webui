#!/usr/bin/env python3
"""
Test the sync function directly to see if it works
"""

import sqlite3
import sys
import os
import time
from datetime import datetime

# Add backend to path  
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_sync_directly():
    """Test the sync function by calling it directly"""
    print("🧪 TESTING: Direct Sync Function Call")
    print("=" * 60)
    
    TARGET_API_KEY = "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"
    
    try:
        # Import the sync function
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        
        # Get user ID
        conn = sqlite3.connect("data/webui.db") 
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM user WHERE email = 'hello@patrykpilat.pl'")
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            print("❌ User not found")
            return False
            
        user_id, user_email = user
        print(f"👤 User: {user_email}")
        print(f"🔑 API Key: {TARGET_API_KEY[:20]}...")
        print()
        
        # Check current organization state
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT co.id, co.name, co.openrouter_api_key, co.updated_at 
            FROM user_client_mapping ucm 
            JOIN client_organizations co ON ucm.client_org_id = co.id 
            WHERE ucm.user_id = ?
        """, (user_id,))
        current_org = cursor.fetchone()
        conn.close()
        
        if current_org:
            print(f"📋 Current Organization: {current_org[1]} (ID: {current_org[0]})")
            print(f"🔑 Current API Key: {current_org[2][:20]}...{current_org[2][-10:]}")
            print(f"⏰ Last Updated: {datetime.fromtimestamp(current_org[3])}")
        
        print(f"\n🔄 Calling sync_ui_key_to_organization...")
        
        # Call the sync function
        result = openrouter_client_manager.sync_ui_key_to_organization(user_id, TARGET_API_KEY)
        
        print(f"📊 Result: {result}")
        
        if result["success"]:
            print("✅ Sync function executed successfully!")
            print(f"📋 Organization: {result.get('organization_updated')}")
            print(f"💬 Message: {result.get('message')}")
            
            # Verify the change
            conn = sqlite3.connect("data/webui.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM client_organizations WHERE openrouter_api_key = ?", (TARGET_API_KEY,))
            updated_org = cursor.fetchone()
            conn.close()
            
            if updated_org:
                print(f"✅ Verified: API key found in database")
                print(f"   Organization: {updated_org[1]}")
                print(f"   API Key: {updated_org[2][:20]}...{updated_org[2][-10:]}")
                return True
            else:
                print("❌ API key not found in database after sync")
                return False
        else:
            print("❌ Sync function failed!")
            print(f"💬 Error: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_sync_directly()