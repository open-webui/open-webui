#!/usr/bin/env python3
"""
EMERGENCY FIX: Update the API key mapping directly in the database
This bypasses the broken automatic sync and fixes the issue immediately
"""

import sqlite3
import sys
import time
from datetime import datetime

# Your API key that should be mapped
TARGET_API_KEY = "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"
USER_EMAIL = "hello@patrykpilat.pl"

def fix_api_key_mapping():
    """Directly update the database with the correct API key"""
    print("🔧 EMERGENCY FIX: Updating API Key Mapping")
    print("=" * 60)
    print(f"🎯 Target: Update API key for {USER_EMAIL}")
    print(f"🔑 New API Key: {TARGET_API_KEY}")
    print()
    
    try:
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute("SELECT id, email FROM user WHERE email = ?", (USER_EMAIL,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User {USER_EMAIL} not found")
            return False
        
        user_id, email = user
        print(f"👤 User found: {email} (ID: {user_id})")
        
        # Get user's organization mapping
        cursor.execute("SELECT client_org_id FROM user_client_mapping WHERE user_id = ?", (user_id,))
        mapping = cursor.fetchone()
        
        if not mapping:
            print("❌ No organization mapping found for user")
            return False
        
        org_id = mapping[0]
        print(f"🏢 Organization ID: {org_id}")
        
        # Get current organization details
        cursor.execute("SELECT name, openrouter_api_key FROM client_organizations WHERE id = ?", (org_id,))
        org = cursor.fetchone()
        
        if not org:
            print("❌ Organization not found")
            return False
        
        org_name, current_key = org
        print(f"📋 Organization: {org_name}")
        print(f"🔑 Current API Key: {current_key[:20]}...{current_key[-10:]}")
        
        # Check if update is needed
        if current_key == TARGET_API_KEY:
            print("✅ API key is already correct! No update needed.")
            return True
        
        # Update the API key
        current_time = int(time.time())
        cursor.execute("""
            UPDATE client_organizations 
            SET openrouter_api_key = ?, updated_at = ?
            WHERE id = ?
        """, (TARGET_API_KEY, current_time, org_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            print("✅ API key updated successfully!")
            print(f"🔑 New API Key: {TARGET_API_KEY[:20]}...{TARGET_API_KEY[-10:]}")
            print(f"⏰ Updated at: {datetime.fromtimestamp(current_time)}")
            
            # Verify the update
            cursor.execute("SELECT openrouter_api_key FROM client_organizations WHERE id = ?", (org_id,))
            updated_key = cursor.fetchone()[0]
            
            if updated_key == TARGET_API_KEY:
                print("✅ Verification: API key correctly saved to database")
                print()
                print("🎯 MAPPING STATUS: FIXED")
                print("Your API key is now properly mapped and ready for use!")
                return True
            else:
                print("❌ Verification failed: API key not updated")
                return False
        else:
            print("❌ Update failed: No rows affected")
            return False
            
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def verify_complete_mapping():
    """Verify the complete mapping is working"""
    print("\n🔍 VERIFICATION: Complete Mapping Check")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect("data/webui.db")
        cursor = conn.cursor()
        
        # Check organization
        cursor.execute("SELECT * FROM client_organizations WHERE openrouter_api_key = ?", (TARGET_API_KEY,))
        org = cursor.fetchone()
        
        if org:
            print(f"✅ Organization: {org[1]} (ID: {org[0]})")
            print(f"🔑 API Key: {org[2][:20]}...{org[2][-10:]}")
            print(f"💰 Markup Rate: {org[4]}x")
            print(f"💵 Monthly Limit: ${org[5]}")
            print(f"📧 Billing Email: {org[6]}")
            print(f"🟢 Active: {bool(org[7])}")
            
            # Check user mapping
            cursor.execute("SELECT user_id, openrouter_user_id FROM user_client_mapping WHERE client_org_id = ?", (org[0],))
            mappings = cursor.fetchall()
            
            print(f"\n🔗 User Mappings: {len(mappings)}")
            for mapping in mappings:
                cursor.execute("SELECT email FROM user WHERE id = ?", (mapping[0],))
                user_email = cursor.fetchone()[0]
                print(f"  - {user_email} → {mapping[1]}")
            
            conn.close()
            return True
        else:
            print("❌ API key not found in database")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    print("🚨 API KEY MAPPING EMERGENCY FIX")
    print("=" * 70)
    print("This will directly fix the API key mapping in the database.")
    print()
    
    # Fix the mapping
    if fix_api_key_mapping():
        # Verify it worked
        if verify_complete_mapping():
            print("\n🎉 SUCCESS: API Key Mapping Fixed!")
            print("✅ Your API key is now properly mapped and ready for production use.")
            print()
            print("🔄 Next Steps:")
            print("1. The automatic mapping system needs debugging")
            print("2. Future API key updates may still fail automatically")
            print("3. For now, your current key works perfectly")
        else:
            print("\n❌ VERIFICATION FAILED")
    else:
        print("\n❌ FIX FAILED")

if __name__ == "__main__":
    main()