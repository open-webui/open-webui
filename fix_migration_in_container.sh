#!/bin/bash
# Script to fix usage tracking migration in Docker container

echo "🚀 Fixing mAI Usage Tracking Migration..."
echo "========================================"

# Run migration
echo "Step 1: Running migration..."
docker exec open-webui-customization bash -c "cd /app/backend && python -c \"
import os
os.environ['WEBUI_SECRET_KEY'] = 'temp-key-for-migration'
try:
    from open_webui.config import run_migrations
    print('Running migrations...')
    run_migrations()
    print('✅ Migration completed!')
except Exception as e:
    print(f'❌ Migration error: {e}')
\""

# Check tables
echo -e "\nStep 2: Checking created tables..."
docker exec open-webui-customization bash -c "cd /app/backend && python -c \"
import sqlite3
conn = sqlite3.connect('data/webui.db')
cursor = conn.cursor()
cursor.execute(\\\"SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'client_%' OR name LIKE 'user_client_%' OR name = 'global_settings')\\\")
tables = cursor.fetchall()
print(f'\\n📊 Found {len(tables)} usage tracking tables:')
for table in tables:
    print(f'  ✓ {table[0]}')
    
# Check if tables have correct structure
print('\\n🔍 Checking table structures:')
for table_name in ['client_organizations', 'user_client_mapping', 'client_live_counters']:
    cursor.execute(f\\\"PRAGMA table_info({table_name})\\\")
    columns = cursor.fetchall()
    if columns:
        print(f'\\n{table_name}: {len(columns)} columns')
    else:
        print(f'\\n❌ {table_name}: NOT FOUND')
        
conn.close()
\""

echo -e "\n✅ Migration check complete!"
echo "Now restart the container: docker restart open-webui-customization"