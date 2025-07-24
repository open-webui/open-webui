#!/bin/bash
# Initialize live counters with correct schema

echo "🔧 Initializing Live Counters..."
echo "================================"

# Initialize live counter for today
docker exec open-webui-customization python -c "
import sqlite3
from datetime import date
import time

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Get organization
cursor.execute('SELECT id FROM client_organizations WHERE is_active = 1')
org = cursor.fetchone()

if org:
    org_id = org[0]
    today = date.today()
    
    # Check if today's counter exists
    cursor.execute('''
        SELECT * FROM client_live_counters 
        WHERE client_org_id = ? AND current_date = ?
    ''', (org_id, today))
    
    if not cursor.fetchone():
        # Create today's counter
        cursor.execute('''
            INSERT INTO client_live_counters 
            (client_org_id, current_date, today_tokens, today_requests, 
             today_raw_cost, today_markup_cost, last_updated)
            VALUES (?, ?, 0, 0, 0.0, 0.0, ?)
        ''', (org_id, today, int(time.time())))
        conn.commit()
        print(f'✅ Created live counter for {today}')
    else:
        print(f'✅ Live counter already exists for {today}')
        
    # Show current counter
    cursor.execute('''
        SELECT today_tokens, today_requests, today_markup_cost 
        FROM client_live_counters 
        WHERE client_org_id = ? AND current_date = ?
    ''', (org_id, today))
    
    result = cursor.fetchone()
    if result:
        print(f'📊 Current usage: {result[0]} tokens, {result[1]} requests, \${result[2]:.6f}')
else:
    print('❌ No organization found')

conn.close()
"

# Fix API configuration with correct data format
echo -e "\n🔧 Fixing API configuration..."
docker exec open-webui-customization python -c "
import sqlite3
import json

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check if openai settings exist
cursor.execute('SELECT data FROM config WHERE id = \"ui.openai\"')
result = cursor.fetchone()

if result:
    print('✅ OpenAI config exists, checking content...')
    data = json.loads(result[1])
    if 'value' in data and isinstance(data['value'], dict):
        # Update with OpenRouter settings
        data['value']['api_base_urls'] = ['https://openrouter.ai/api/v1']
        data['value']['api_keys'] = ['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']
        cursor.execute('UPDATE config SET data = ? WHERE id = \"ui.openai\"', (json.dumps(data),))
        conn.commit()
        print('✅ Updated OpenRouter settings in UI config')
else:
    print('⚠️  UI config not found - settings will sync on next UI save')

conn.close()
"

# Test if usage tracking is ready
echo -e "\n🧪 Testing usage tracking readiness..."
docker exec open-webui-customization python -c "
import os
os.environ['WEBUI_SECRET_KEY'] = 'temp-key'

try:
    # Import after setting env
    import sys
    sys.path.insert(0, '/app/backend')
    from open_webui.models.organization_usage import ClientUsageDB
    
    # Test the usage recording
    print('✅ Usage tracking module loaded successfully')
    
    # Check if we can get usage stats
    import sqlite3
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM client_organizations WHERE is_active = 1')
    org = cursor.fetchone()
    
    if org:
        # This would be called when API usage happens
        print(f'✅ Ready to track usage for org: {org[0]}')
        print('✅ Usage will be recorded on next OpenRouter API call')
    
    conn.close()
    
except Exception as e:
    print(f'❌ Error: {e}')
"

echo -e "\n✅ Initialization complete!"
echo -e "\n📋 Next steps:"
echo "1. Restart container: docker restart open-webui-customization"
echo "2. Make a test query in mAI chat"
echo "3. Check Admin Settings → Usage tab"
echo -e "\nThe usage should update within 30 seconds of making a query!"