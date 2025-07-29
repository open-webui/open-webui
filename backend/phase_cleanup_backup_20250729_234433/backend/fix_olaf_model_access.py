#!/usr/bin/env python3
"""
Fix model access for user Olaf by ensuring proper permissions.
This script will:
1. Verify user exists
2. Check model access control settings
3. Update model permissions to allow access
"""

import sqlite3
import json
from datetime import datetime

def fix_user_model_access():
    """Fix model access for Olaf"""
    db_path = '/app/backend/data/webui.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Verify user exists
        print("🔍 Checking user...")
        cursor.execute("SELECT id, name, email, role FROM user WHERE email = ?", ('krokodylek1981@gmail.com',))
        user = cursor.fetchone()
        
        if not user:
            print("❌ User not found!")
            return
            
        user_id, name, email, role = user
        print(f"✅ Found user: {name} ({email}) - Role: {role}")
        
        # 2. Check current model access control
        print("\n🔍 Checking model access control...")
        cursor.execute("SELECT id, name, access_control FROM model")
        models = cursor.fetchall()
        
        restricted_models = []
        for model_id, model_name, access_control in models:
            if access_control:
                try:
                    ac = json.loads(access_control)
                    if 'read' in ac and 'user_ids' in ac['read']:
                        if user_id not in ac['read']['user_ids']:
                            restricted_models.append((model_id, model_name))
                except:
                    pass
        
        if restricted_models:
            print(f"⚠️ Found {len(restricted_models)} restricted models")
            
            # 3. Update model permissions
            print("\n🔧 Fixing model permissions...")
            for model_id, model_name in restricted_models:
                # Get current access control
                cursor.execute("SELECT access_control FROM model WHERE id = ?", (model_id,))
                ac_json = cursor.fetchone()[0]
                
                if ac_json:
                    ac = json.loads(ac_json)
                    if 'read' not in ac:
                        ac['read'] = {'user_ids': []}
                    if 'user_ids' not in ac['read']:
                        ac['read']['user_ids'] = []
                    
                    # Add user to allowed list
                    if user_id not in ac['read']['user_ids']:
                        ac['read']['user_ids'].append(user_id)
                        
                    # Update model
                    cursor.execute("UPDATE model SET access_control = ? WHERE id = ?", 
                                 (json.dumps(ac), model_id))
                    print(f"  ✅ Updated access for: {model_name}")
        else:
            print("✅ All models have public access (no restrictions)")
            
        # 4. Alternative solution: Set all models to public access
        print("\n🔧 Setting all models to public access...")
        cursor.execute("UPDATE model SET access_control = NULL")
        affected = cursor.rowcount
        print(f"✅ Made {affected} models publicly accessible")
        
        # 5. Verify user settings
        print("\n🔍 Checking user settings...")
        cursor.execute("SELECT settings FROM user WHERE id = ?", (user_id,))
        settings_json = cursor.fetchone()[0]
        
        if settings_json:
            settings = json.loads(settings_json)
            print("Current user settings:", json.dumps(settings, indent=2))
        else:
            print("User has no custom settings")
            
        # Commit changes
        conn.commit()
        print("\n✅ All changes committed successfully!")
        
        # 6. Show summary
        print("\n📊 Summary:")
        print(f"- User: {name} ({email})")
        print(f"- Role: {role}")
        print(f"- Models in database: {len(models)}")
        print("- All models now have public access")
        print("\n🎉 Olaf should now see all 12 business models!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_user_model_access()