#!/usr/bin/env python3
import sqlite3
import time
import uuid

# Database path
db_path = "./backend/data/webui.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create default client organization
org_id = f"client_default_organization_{int(time.time())}"
current_time = int(time.time())

# Insert default organization (using the OpenRouter API key from the config)
cursor.execute("""
    INSERT INTO client_organizations 
    (id, name, openrouter_api_key, openrouter_key_hash, markup_rate, monthly_limit, billing_email, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    org_id,
    "Default Organization", 
    "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",  # Your OpenRouter key
    "default_hash",
    1.3,
    1000.0,
    "admin@example.com",
    1,
    current_time,
    current_time
))

# Get the user ID from the users table
cursor.execute("SELECT id FROM user LIMIT 1")
user_result = cursor.fetchone()

if user_result:
    user_id = user_result[0]
    mapping_id = str(uuid.uuid4())
    
    # Create user-client mapping
    cursor.execute("""
        INSERT INTO user_client_mapping 
        (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        mapping_id,
        user_id,
        org_id,
        f"openrouter_{user_id}",
        1,
        current_time,
        current_time
    ))
    
    print(f"✅ Created client organization: {org_id}")
    print(f"✅ Mapped user {user_id} to organization")
    print(f"✅ OpenRouter user ID: openrouter_{user_id}")
else:
    print("❌ No users found in database")

conn.commit()
conn.close()

print("🚀 Client organization setup complete!")