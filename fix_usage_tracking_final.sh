#!/bin/bash
# Final fix for usage tracking

echo "🔧 Fixing mAI Usage Tracking Issues..."
echo "====================================="

# 1. Check correct column names in tables
echo -e "\n1️⃣ Checking table structure..."
docker exec open-webui-customization python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check client_live_counters columns
cursor.execute('PRAGMA table_info(client_live_counters)')
columns = cursor.fetchall()
print('client_live_counters columns:')
for col in columns:
    print(f'  - {col[1]} ({col[2]})')

conn.close()
"

# 2. Initialize live counters for existing organization
echo -e "\n2️⃣ Initializing live counters..."
docker exec open-webui-customization python -c "
import sqlite3
import uuid
from datetime import date

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Get organization ID
cursor.execute('SELECT id FROM client_organizations WHERE is_active = 1')
org = cursor.fetchone()

if org:
    org_id = org[0]
    print(f'Found org: {org_id}')
    
    # Check if counter exists
    cursor.execute('SELECT id FROM client_live_counters WHERE client_org_id = ?', (org_id,))
    if not cursor.fetchone():
        # Create counter
        counter_id = str(uuid.uuid4())
        today = date.today().isoformat()
        
        # Get correct column names first
        cursor.execute('PRAGMA table_info(client_live_counters)')
        columns = [col[1] for col in cursor.fetchall()]
        print(f'Available columns: {columns}')
        
        # Insert based on actual columns
        if 'tokens' in columns:
            # New schema
            cursor.execute('''
                INSERT INTO client_live_counters 
                (id, client_org_id, tokens, requests, cost, last_reset_date, updated_at)
                VALUES (?, ?, 0, 0, 0.0, ?, 0)
            ''', (counter_id, org_id, today))
        else:
            # Old schema - try the most likely column names
            cursor.execute('''
                INSERT INTO client_live_counters 
                (id, client_org_id, total_tokens, total_requests, raw_cost, markup_cost, last_reset_date, updated_at)
                VALUES (?, ?, 0, 0, 0.0, 0.0, ?, 0)
            ''', (counter_id, org_id, today))
        
        conn.commit()
        print('✅ Created live counter')
    else:
        print('✅ Live counter already exists')
else:
    print('❌ No organization found')

conn.close()
"

# 3. Force sync API settings
echo -e "\n3️⃣ Syncing API settings..."
docker exec open-webui-customization python -c "
import os
os.environ['WEBUI_SECRET_KEY'] = 'temp-key'

import sqlite3
import json

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Your OpenRouter configuration
api_key = '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'
base_url = 'https://openrouter.ai/api/v1'

# Check current settings
cursor.execute('SELECT id, data FROM config WHERE id = \"openai_api_keys\"')
result = cursor.fetchone()

if result:
    # Update existing
    data = json.loads(result[1])
    data['value'] = [api_key]  # Set as list
    cursor.execute('UPDATE config SET data = ? WHERE id = \"openai_api_keys\"', (json.dumps(data),))
    print('✅ Updated API keys')
else:
    # Insert new
    data = {'value': [api_key]}
    cursor.execute('INSERT INTO config (id, data) VALUES (\"openai_api_keys\", ?)', (json.dumps(data),))
    print('✅ Inserted API keys')

# Same for base URLs
cursor.execute('SELECT id, data FROM config WHERE id = \"openai_api_base_urls\"')
result = cursor.fetchone()

if result:
    data = json.loads(result[1])
    data['value'] = [base_url]
    cursor.execute('UPDATE config SET data = ? WHERE id = \"openai_api_base_urls\"', (json.dumps(data),))
    print('✅ Updated base URLs')
else:
    data = {'value': [base_url]}
    cursor.execute('INSERT INTO config (id, data) VALUES (\"openai_api_base_urls\", ?)', (json.dumps(data),))
    print('✅ Inserted base URLs')

conn.commit()
conn.close()
"

# 4. Update organization API key to ensure it matches
echo -e "\n4️⃣ Ensuring organization has correct API key..."
docker exec open-webui-customization python -c "
import sqlite3

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

api_key = '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'

cursor.execute('UPDATE client_organizations SET openrouter_api_key = ? WHERE is_active = 1', (api_key,))
conn.commit()

print('✅ Updated organization API key')
conn.close()
"

# 5. Final check
echo -e "\n5️⃣ Final verification..."
docker exec open-webui-customization python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check everything is connected
cursor.execute('''
    SELECT co.name, co.openrouter_api_key, um.user_id, um.openrouter_user_id 
    FROM client_organizations co
    JOIN user_client_mapping um ON co.id = um.client_org_id
    WHERE co.is_active = 1
''')
result = cursor.fetchone()

if result:
    print(f'✅ Organization: {result[0]}')
    print(f'✅ API Key: {result[1][:20]}...')
    print(f'✅ User ID: {result[2]}')
    print(f'✅ External User: {result[3]}')
    print('\n🎉 Everything is properly connected!')
else:
    print('❌ Missing connections')

conn.close()
"

echo -e "\n✅ Fix complete! Now restart the container:"
echo "docker restart open-webui-customization"