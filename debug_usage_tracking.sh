#!/bin/bash
# Debug usage tracking issues

echo "🔍 Debugging mAI Usage Tracking..."
echo "=================================="

# 1. Check database contents
echo -e "\n1️⃣ Checking database contents..."
docker exec open-webui-customization python -c "
import sqlite3
import json

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check organizations
print('\n=== Organizations ===')
cursor.execute('SELECT id, name, openrouter_api_key, is_active FROM client_organizations')
orgs = cursor.fetchall()
if orgs:
    for org in orgs:
        print(f'ID: {org[0]}')
        print(f'Name: {org[1]}')
        print(f'API Key: {org[2][:20]}...' if org[2] else 'No key')
        print(f'Active: {org[3]}')
        print('---')
else:
    print('❌ No organizations found!')

# Check user mappings
print('\n=== User Mappings ===')
cursor.execute('SELECT um.user_id, um.client_org_id, um.openrouter_user_id, u.email FROM user_client_mapping um LEFT JOIN user u ON um.user_id = u.id')
mappings = cursor.fetchall()
if mappings:
    for m in mappings:
        print(f'User: {m[3]} (ID: {m[0]})')
        print(f'Org: {m[1]}')
        print(f'External User: {m[2] or \"Not set\"}')
        print('---')
else:
    print('❌ No user mappings found!')

# Check live counters
print('\n=== Live Counters ===')
cursor.execute('SELECT client_org_id, total_tokens, total_requests, markup_cost FROM client_live_counters')
counters = cursor.fetchall()
if counters:
    for c in counters:
        print(f'Org: {c[0]}, Tokens: {c[1]}, Requests: {c[2]}, Cost: ${c[3]}')
else:
    print('❌ No live counters found!')

conn.close()
"

# 2. Check admin user
echo -e "\n2️⃣ Checking admin user..."
docker exec open-webui-customization python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT id, email, role FROM user WHERE role = \"admin\" LIMIT 1')
admin = cursor.fetchone()
if admin:
    print(f'Admin: {admin[1]} (ID: {admin[0]})')
else:
    print('❌ No admin user found!')
conn.close()
"

# 3. Check API configuration
echo -e "\n3️⃣ Checking API configuration..."
docker exec open-webui-customization python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check settings for OpenRouter
cursor.execute(\"SELECT data FROM config WHERE id IN ('openai_api_base_urls', 'openai_api_keys')\")
configs = cursor.fetchall()
for config in configs:
    data = config[0]
    if 'openrouter' in data.lower():
        print('✅ OpenRouter configured in settings')
        break
else:
    print('⚠️  OpenRouter not found in API settings')

conn.close()
"

# 4. Test usage recording function
echo -e "\n4️⃣ Testing usage recording..."
docker exec open-webui-customization python -c "
import sys
sys.path.insert(0, '/app/backend')

try:
    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
    
    # Test data from your OpenRouter response
    test_usage = {
        'model': 'deepseek/deepseek-chat-v3-0324',
        'prompt_tokens': 653,
        'completion_tokens': 19,
        'cost': 0.000354,
        'external_user': 'openrouter_86b5496d-52c8-40f3-a9b1-098560aeb395'
    }
    
    # Get admin user ID (you'll need to replace this with actual user ID)
    import sqlite3
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM user WHERE role = \"admin\" LIMIT 1')
    admin = cursor.fetchone()
    
    if admin:
        user_id = admin[0]
        print(f'Testing with user ID: {user_id}')
        
        # Try to get user context
        context = openrouter_client_manager.get_user_client_context(user_id)
        print(f'Context: {context}')
        
        if not context['client_org_id']:
            print('❌ No organization mapping for user!')
        else:
            print(f'✅ User mapped to org: {context[\"client_org_id\"]}')
    else:
        print('❌ No admin user to test with')
        
    conn.close()
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"

echo -e "\n✅ Debug check complete!"
echo "Look for any ❌ errors above to identify the issue."