#!/usr/bin/env python3
"""
Test script to verify OpenRouter usage recording
"""

import subprocess
import time
import json

def check_usage_tables():
    """Check current state of usage tables"""
    cmd = [
        "docker", "exec", "open-webui-customization", "python", "-c",
        """
import sqlite3
from datetime import datetime
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

print('\\n=== CHECKING USAGE TABLES ===')
print(f'Timestamp: {datetime.now().isoformat()}')

# Check client_user_daily_usage
cursor.execute('SELECT COUNT(*) FROM client_user_daily_usage')
user_count = cursor.fetchone()[0]
print(f'\\nUser daily usage records: {user_count}')

if user_count > 0:
    cursor.execute('''
        SELECT user_id, openrouter_user_id, total_tokens, total_requests, 
               raw_cost, markup_cost, created_at 
        FROM client_user_daily_usage 
        ORDER BY created_at DESC LIMIT 5
    ''')
    print('\\nLatest user usage records:')
    for row in cursor.fetchall():
        print(f'  User: {row[0][:8]}..., External: {row[1]}')
        print(f'  Tokens: {row[2]}, Requests: {row[3]}')
        print(f'  Cost: ${row[4]:.6f} (raw) / ${row[5]:.6f} (markup)')
        print(f'  Created: {row[6]}')
        print()

# Check client_model_daily_usage
cursor.execute('SELECT COUNT(*) FROM client_model_daily_usage')
model_count = cursor.fetchone()[0]
print(f'Model daily usage records: {model_count}')

if model_count > 0:
    cursor.execute('''
        SELECT model_name, provider, total_tokens, total_requests,
               raw_cost, markup_cost, created_at
        FROM client_model_daily_usage
        ORDER BY created_at DESC LIMIT 5
    ''')
    print('\\nLatest model usage records:')
    for row in cursor.fetchall():
        print(f'  Model: {row[0]}')
        print(f'  Provider: {row[1]}')
        print(f'  Tokens: {row[2]}, Requests: {row[3]}')
        print(f'  Cost: ${row[4]:.6f} (raw) / ${row[5]:.6f} (markup)')
        print(f'  Created: {row[6]}')
        print()

conn.close()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

def check_recent_logs():
    """Check recent logs for usage recording attempts"""
    cmd = [
        "docker", "logs", "open-webui-customization", "--tail", "50"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    
    # Filter for relevant log lines
    relevant_logs = []
    for line in result.stderr.split('\n'):
        if any(keyword in line for keyword in [
            'Recording usage',
            'Recorded usage',
            'Failed to record',
            'openrouter_client_manager',
            'Usage data',
            'external_user'
        ]):
            relevant_logs.append(line)
    
    if relevant_logs:
        print("\n=== RECENT USAGE RECORDING LOGS ===")
        for log in relevant_logs[-10:]:  # Last 10 relevant logs
            print(log)
    else:
        print("\n=== NO RECENT USAGE RECORDING LOGS FOUND ===")

def main():
    print("🔍 OpenRouter Usage Recording Test")
    print("=" * 50)
    
    # Check current state
    check_usage_tables()
    
    # Check logs
    check_recent_logs()
    
    print("\n📊 Summary:")
    print("1. Check if usage tables have any records")
    print("2. Review logs for any recording attempts or errors")
    print("3. Make a query through mAI UI to generate usage data")
    print("4. Run this script again to verify recording")

if __name__ == "__main__":
    main()