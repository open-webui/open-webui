#!/usr/bin/env python3
"""
Check if the latest OpenRouter call was recorded in the database
"""
import sqlite3
from datetime import datetime

db_path = "./backend/data/webui.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 Checking Latest OpenRouter Call Recording")
print("=" * 60)

# Details from the OpenRouter response
external_user = "openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395"
expected_tokens = 430  # 409 + 21
expected_cost = 0.000117776
expected_time = "2025-07-24T14:28:59"

print(f"📊 Expected from OpenRouter:")
print(f"   External User: {external_user}")
print(f"   Total Tokens: {expected_tokens}")
print(f"   Raw Cost: ${expected_cost}")
print(f"   Created At: {expected_time}")

# 1. Check if user exists with this external_user
print(f"\n1️⃣ Checking user mapping:")
cursor.execute("""
    SELECT user_id, client_org_id 
    FROM user_client_mapping 
    WHERE openrouter_user_id = ? AND is_active = 1
""", (external_user,))

user_mapping = cursor.fetchone()
if user_mapping:
    user_id, client_org_id = user_mapping
    print(f"✅ Found user mapping: {user_id} → {client_org_id}")
else:
    print(f"❌ No user mapping found for {external_user}")
    
    # Check what mappings exist
    cursor.execute("SELECT openrouter_user_id FROM user_client_mapping WHERE is_active = 1")
    existing = cursor.fetchall()
    print(f"   Existing mappings: {[row[0] for row in existing]}")

# 2. Check live counters for today
print(f"\n2️⃣ Checking today's live counters:")
cursor.execute("""
    SELECT client_org_id, today_tokens, today_requests, today_raw_cost, 
           today_markup_cost, last_updated
    FROM client_live_counters 
    WHERE current_date = '2025-07-24'
""")

live_data = cursor.fetchall()
if live_data:
    for row in live_data:
        last_updated = datetime.fromtimestamp(row[5]).strftime('%Y-%m-%d %H:%M:%S')
        print(f"   Client: {row[0]}")
        print(f"   Tokens: {row[1]} (expected {expected_tokens})")
        print(f"   Requests: {row[2]}")
        print(f"   Raw Cost: ${row[3]} (expected ${expected_cost})")
        print(f"   Markup Cost: ${row[4]}")
        print(f"   Last Updated: {last_updated}")
        
        # Check if this matches our expected data
        expected_time_obj = datetime.fromisoformat(expected_time.replace('T', ' ').replace('+00:00', ''))
        if row[1] >= expected_tokens and row[3] >= expected_cost:
            print(f"   ✅ Data appears to include our request")
        else:
            print(f"   ❌ Data doesn't match our request")
else:
    print("❌ No live counter data found for today")

# 3. Check user daily usage
print(f"\n3️⃣ Checking user daily usage:")
if user_mapping:
    cursor.execute("""
        SELECT total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at
        FROM client_user_daily_usage 
        WHERE user_id = ? AND usage_date = '2025-07-24'
    """, (user_id,))
    
    user_usage = cursor.fetchone()
    if user_usage:
        created_at = datetime.fromtimestamp(user_usage[4]).strftime('%Y-%m-%d %H:%M:%S')
        updated_at = datetime.fromtimestamp(user_usage[5]).strftime('%Y-%m-%d %H:%M:%S')
        print(f"   Tokens: {user_usage[0]}")
        print(f"   Requests: {user_usage[1]}")
        print(f"   Raw Cost: ${user_usage[2]}")
        print(f"   Markup Cost: ${user_usage[3]}")
        print(f"   Created: {created_at}")
        print(f"   Updated: {updated_at}")
    else:
        print("❌ No user daily usage found")

# 4. Check model usage
print(f"\n4️⃣ Checking model usage:")
cursor.execute("""
    SELECT model_name, total_tokens, total_requests, raw_cost, markup_cost
    FROM client_model_daily_usage 
    WHERE usage_date = '2025-07-24' AND model_name = 'deepseek/deepseek-chat-v3-0324'
""")

model_usage = cursor.fetchone()
if model_usage:
    print(f"   Model: {model_usage[0]}")
    print(f"   Tokens: {model_usage[1]}")
    print(f"   Requests: {model_usage[2]}")
    print(f"   Raw Cost: ${model_usage[3]}")
    print(f"   Markup Cost: ${model_usage[4]}")
else:
    print("❌ No model usage found for deepseek/deepseek-chat-v3-0324")

# 5. Summary
print(f"\n5️⃣ Summary:")
if not user_mapping:
    print("🚨 PROBLEM: User mapping doesn't exist for the external_user from OpenRouter")
    print("   This means the usage recording will fail because the system can't")
    print("   identify which organization this user belongs to.")
    
    print(f"\n💡 SOLUTION: Create user mapping")
    print(f"   The external_user from OpenRouter: {external_user}")
    print(f"   Extract user_id: {external_user.replace('openrouter_', '')}")
    
    # Check if this user actually exists
    potential_user_id = external_user.replace('openrouter_', '')
    cursor.execute("SELECT id, email FROM user WHERE id = ?", (potential_user_id,))
    user_check = cursor.fetchone()
    if user_check:
        print(f"   ✅ User exists: {user_check[1]} ({user_check[0]})")
        print("   Need to create mapping for this user.")
    else:
        print(f"   ❌ User {potential_user_id} doesn't exist in database")

conn.close()