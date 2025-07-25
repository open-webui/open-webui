#!/usr/bin/env python3
import json
import sqlite3

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

cursor.execute("SELECT data FROM config WHERE id = 1")
row = cursor.fetchone()

if row:
    config = json.loads(row[0])
    openai_config = config.get("openai", {}).get("api_configs", {}).get("0", {})
    
    print("✅ OpenRouter Configuration:")
    print(f"   Enabled: {openai_config.get('enable', False)}")
    print(f"   Model count: {len(openai_config.get('model_ids', []))}")
    print(f"   Connection type: {openai_config.get('connection_type', 'N/A')}")
    print(f"   Tags: {openai_config.get('tags', [])}")
    
    if openai_config.get('model_ids'):
        print("\n📋 Configured models:")
        for model in openai_config.get('model_ids', []):
            print(f"   - {model}")

conn.close()