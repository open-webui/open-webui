#!/usr/bin/env python3
"""Run the usage tracking migration"""

import sys
import os
sys.path.insert(0, '/app/backend')

try:
    from open_webui.config import run_migrations
    print("Running migrations...")
    run_migrations()
    print("✅ Migrations completed successfully!")
    
    # Verify tables were created
    import sqlite3
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'client_%' OR name LIKE 'user_client%')")
    tables = cursor.fetchall()
    print(f"\n✅ Created {len(tables)} usage tracking tables:")
    for table in tables:
        print(f"   - {table[0]}")
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)