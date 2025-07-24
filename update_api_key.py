#!/usr/bin/env python3
"""
Update OpenRouter API key in the database
"""
import sqlite3

# Database path
db_path = "./backend/data/webui.db"

# New correct API key
new_api_key = "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"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Update the API key in client_organizations table
cursor.execute("""
    UPDATE client_organizations 
    SET openrouter_api_key = ?
    WHERE is_active = 1
""", (new_api_key,))

rows_updated = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Updated API key in {rows_updated} organization(s)")
print(f"🔑 New API key: {new_api_key[:20]}...")
print("🚀 Database updated successfully!")