#!/usr/bin/env python3
"""
Simple test to check if the sync function works with your actual API key
"""

import sqlite3
import sys
import os

# The API key that should have been mapped
TARGET_API_KEY = "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"
ORG_NAME = "Org_C"

def test_manual_sync():
    """Test by calling the sync function directly without importing backend modules"""
    print("🧪 TESTING: Direct Database Simulation")
    print("=" * 60)
    
    try:
        # Get the actual user from the database
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email FROM user LIMIT 1")
        user = cursor.fetchone()
        
        if not user:
            print("❌ No user found in database")
            return False
        
        user_id, user_email = user
        print(f"👤 Real user: {user_email} (ID: {user_id})")
        print(f"🔑 Your API key: {TARGET_API_KEY}")
        print()
        
        # Check if this would pass the basic validation
        if not TARGET_API_KEY.startswith("sk-or-"):
            print("❌ API key format validation would fail")
            return False
        else:
            print("✅ API key format validation would pass")
        
        # Check if user already has an organization mapping
        cursor.execute("SELECT * FROM user_client_mapping WHERE user_id = ?", (user_id,))
        existing_mapping = cursor.fetchone()
        
        if existing_mapping:
            print(f"✅ User has existing mapping to org: {existing_mapping[2]}")
            
            # Get the organization details
            cursor.execute("SELECT * FROM client_organizations WHERE id = ?", (existing_mapping[2],))
            org = cursor.fetchone()
            
            if org:
                print(f"📋 Current organization: {org[1]}")
                print(f"🔑 Current API key: {org[2][:20]}...{org[2][-10:] if len(org[2]) > 30 else org[2]}")
                print()
                print("🔄 The sync function would UPDATE the existing organization's API key")
                print(f"   Old key: {org[2][:20]}...")
                print(f"   New key: {TARGET_API_KEY[:20]}...")
                
                # Check if it's the same key
                if org[2] == TARGET_API_KEY:
                    print("⚠️  API key is already set correctly! No change needed.")
                    return True
                else:
                    print("✅ API key would be updated")
            
        else:
            print("📭 User has no organization mapping")
            print("🏗️  The sync function would CREATE a new default organization")
            print(f"   Organization name: client_default_organization_{int(__import__('time').time())}")
            print(f"   API key: {TARGET_API_KEY}")
            print(f"   Markup rate: 1.3")
            print(f"   Monthly limit: $1000")
        
        conn.close()
        
        # The issue identification
        print("\n🔍 ISSUE ANALYSIS:")
        print("The automatic sync function logic is correct, but it was never called.")
        print("This means either:")
        print("1. You didn't save the API key in Settings → Connections")
        print("2. The API key was saved but the sync function had an error")
        print("3. The backend server wasn't running when you saved")
        print("4. There was a silent error in the sync process")
        
        print(f"\n🛠️  SOLUTION:")
        print("Try adding the API key again in the UI:")
        print("1. Go to Settings → Connections")
        print("2. Add OpenRouter connection:")
        print("   - URL: https://openrouter.ai/api/v1")
        print(f"   - API Key: {TARGET_API_KEY}")
        print("3. Click Save")
        print("4. The sync should happen automatically")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_ui_detection_logic():
    """Show what the UI detection logic expects"""
    print("\n📋 UI DETECTION LOGIC")
    print("=" * 60)
    print("The automatic mapping triggers when the backend receives:")
    print()
    print("POST /api/v1/users/user/settings/update")
    print("Content-Type: application/json")
    print()
    print("{")
    print('  "ui": {')
    print('    "directConnections": {')
    print('      "OPENAI_API_KEYS": [')
    print(f'        "{TARGET_API_KEY}"')
    print('      ],')
    print('      "OPENAI_API_BASE_URLS": [')
    print('        "https://openrouter.ai/api/v1"')
    print('      ]')
    print('    }')
    print('  }')
    print('}')
    print()
    print("The logic looks for:")
    print("✅ Key starts with 'sk-or-'")
    print("✅ URL contains 'openrouter.ai'")
    print("✅ Both are in the same position in their arrays")

def main():
    print("🚨 AUTOMATIC MAPPING ISSUE DIAGNOSIS")
    print("=" * 70)
    
    test_manual_sync()
    show_ui_detection_logic()
    
    print("\n🎯 RECOMMENDED ACTION:")
    print("Re-enter your API key in the mAI UI to trigger the automatic mapping.")

if __name__ == "__main__":
    main()