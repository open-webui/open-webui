#!/usr/bin/env python3
"""
Fix user mapping to match the current OpenRouter external_user
"""
import sqlite3
import time

db_path = "./backend/data/webui.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔧 Fixing User Mapping")
print("=" * 40)

# Current user in database
cursor.execute("SELECT id, email FROM user WHERE role = 'admin' LIMIT 1")
user_data = cursor.fetchone()
current_user_id = user_data[0]
user_email = user_data[1]

print(f"✅ Current user: {user_email} ({current_user_id})")

# Clear the external_user so it will be auto-learned on next API call
print(f"🔄 Clearing external_user mapping for auto-learning")

# Update the user mapping to empty string so it will be auto-learned
# (Using empty string because database has NOT NULL constraint)
cursor.execute("""
    UPDATE user_client_mapping 
    SET openrouter_user_id = '', updated_at = ?
    WHERE user_id = ? AND is_active = 1
""", (int(time.time()), current_user_id))

rows_updated = cursor.rowcount

if rows_updated > 0:
    print(f"✅ Updated {rows_updated} user mapping(s)")
    
    # Verify the update
    cursor.execute("""
        SELECT user_id, client_org_id, openrouter_user_id 
        FROM user_client_mapping 
        WHERE user_id = ? AND is_active = 1
    """, (current_user_id,))
    
    updated_mapping = cursor.fetchone()
    print(f"✅ Verified mapping: {updated_mapping[0]} → {updated_mapping[1]}")
    print(f"✅ OpenRouter user: {updated_mapping[2] or 'Will be auto-learned'}")
else:
    print("❌ No mappings were updated")

conn.commit()
conn.close()

print("\n🚀 User mapping prepared for auto-learning!")
print("💡 The external_user will be automatically detected and saved on your next API call.")
print("💡 Make an API call through mAI to test the auto-learning feature.")