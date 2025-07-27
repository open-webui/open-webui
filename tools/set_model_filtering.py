#!/usr/bin/env python3
"""
Script to set model filtering configuration directly in the database.
This configures the OpenRouter connection to show only 12 specific models.
"""

import json
import sqlite3
import sys
from datetime import datetime

# The 12 allowed models configuration
MODEL_CONFIG = {
    "0": {
        "enable": True,
        "connection_type": "external",
        "model_ids": [
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-pro",
            "deepseek/deepseek-chat-v3-0324",
            "anthropic/claude-3.7-sonnet",
            "google/gemini-2.5-flash-lite-preview-06-17",
            "openai/gpt-4.1",
            "x-ai/grok-4",
            "openai/gpt-4o-mini",
            "openai/o4-mini-high",
            "openai/o3",
            "openai/chatgpt-4o-latest"
        ],
        "tags": ["openrouter"]
    }
}

def update_database(db_path="backend/data/webui.db"):
    """Update the database with model filtering configuration."""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current config structure
        cursor.execute('SELECT data FROM config ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        if result:
            # Load existing config
            config_data = json.loads(result[0])
            print(f"Current config keys: {list(config_data.keys())}")
            
            # Add/update OpenAI configuration
            if 'openai' not in config_data:
                config_data['openai'] = {}
            
            config_data['openai']['api_configs'] = MODEL_CONFIG
            
            # Update database
            updated_json = json.dumps(config_data)
            timestamp = datetime.now().isoformat()
            
            cursor.execute(
                'UPDATE config SET data = ?, updated_at = ? WHERE id = (SELECT MAX(id) FROM config)',
                (updated_json, timestamp)
            )
            
            conn.commit()
            print("✓ Model filtering configuration updated successfully!")
            print(f"✓ Configured {len(MODEL_CONFIG['0']['model_ids'])} allowed models")
            
        else:
            # Create new config if none exists
            config_data = {
                "version": 1,
                "openai": {
                    "api_configs": MODEL_CONFIG
                }
            }
            
            config_json = json.dumps(config_data)
            timestamp = datetime.now().isoformat()
            
            cursor.execute(
                'INSERT INTO config (data, version, created_at, updated_at) VALUES (?, 1, ?, ?)',
                (config_json, timestamp, timestamp)
            )
            
            conn.commit()
            print("✓ New configuration created with model filtering!")
        
        # Verify the update
        cursor.execute('SELECT data FROM config ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        if result:
            updated_config = json.loads(result[0])
            if 'openai' in updated_config and 'api_configs' in updated_config['openai']:
                model_count = len(updated_config['openai']['api_configs']['0']['model_ids'])
                print(f"✓ Verification: {model_count} models configured")
            else:
                print("✗ Verification failed: Configuration not found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error updating database: {e}")
        return False

def show_current_config(db_path="backend/data/webui.db"):
    """Show current configuration in database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM config ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        if result:
            config_data = json.loads(result[0])
            print("Current configuration:")
            if 'openai' in config_data and 'api_configs' in config_data['openai']:
                api_configs = config_data['openai']['api_configs']
                print(json.dumps(api_configs, indent=2))
            else:
                print("No OpenAI API configurations found")
        else:
            print("No configuration found in database")
            
        conn.close()
        
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage OpenRouter model filtering configuration")
    parser.add_argument("--show", action="store_true", help="Show current configuration")
    parser.add_argument("--update", action="store_true", help="Update configuration with model filtering")
    parser.add_argument("--db", default="backend/data/webui.db", help="Database path")
    
    args = parser.parse_args()
    
    if args.show:
        show_current_config(args.db)
    elif args.update:
        if update_database(args.db):
            print("\n🎉 Model filtering is now configured!")
            print("Please restart the application to apply changes.")
            print("\nThe following 12 models will be available:")
            for i, model in enumerate(MODEL_CONFIG['0']['model_ids'], 1):
                print(f"  {i:2d}. {model}")
        else:
            sys.exit(1)
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python set_model_filtering.py --show")
        print("  python set_model_filtering.py --update")