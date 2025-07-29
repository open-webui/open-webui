#!/usr/bin/env python3
"""
Script to register OpenRouter models in the Models table.
This makes the models visible to all users with appropriate permissions.
"""

import json
import sqlite3
import time
from datetime import datetime
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The 12 business models from OpenRouter
OPENROUTER_MODELS = [
    {
        "id": "anthropic/claude-sonnet-4",
        "name": "Claude 3.5 Sonnet v2",
        "description": "Anthropic's latest Claude model with improved capabilities"
    },
    {
        "id": "google/gemini-2.5-flash",
        "name": "Gemini 2.0 Flash",
        "description": "Google's fast and efficient AI model"
    },
    {
        "id": "google/gemini-2.5-pro",
        "name": "Gemini 2.0 Pro",
        "description": "Google's advanced AI model for complex tasks"
    },
    {
        "id": "deepseek/deepseek-chat-v3-0324",
        "name": "DeepSeek Chat V3",
        "description": "DeepSeek's conversational AI model"
    },
    {
        "id": "anthropic/claude-3.7-sonnet",
        "name": "Claude 3 Sonnet",
        "description": "Anthropic's balanced Claude model"
    },
    {
        "id": "google/gemini-2.5-flash-lite-preview-06-17",
        "name": "Gemini 2.0 Flash Lite Preview",
        "description": "Google's lightweight preview model"
    },
    {
        "id": "openai/gpt-4.1",
        "name": "GPT-4 Turbo",
        "description": "OpenAI's GPT-4 Turbo model"
    },
    {
        "id": "x-ai/grok-4",
        "name": "Grok 2",
        "description": "xAI's Grok model"
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "description": "OpenAI's efficient small model"
    },
    {
        "id": "openai/o4-mini-high",
        "name": "O1 Mini",
        "description": "OpenAI's reasoning model (mini version)"
    },
    {
        "id": "openai/o3",
        "name": "O1",
        "description": "OpenAI's advanced reasoning model"
    },
    {
        "id": "openai/chatgpt-4o-latest",
        "name": "ChatGPT-4o",
        "description": "OpenAI's latest ChatGPT model"
    }
]

def get_admin_user_id(cursor):
    """Get the ID of an admin user to set as model owner."""
    cursor.execute("SELECT id FROM user WHERE role = 'admin' LIMIT 1")
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # If no admin, get any user
    cursor.execute("SELECT id FROM user LIMIT 1")
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Create a system user if no users exist
    user_id = "system"
    timestamp = int(time.time())
    cursor.execute(
        """INSERT OR IGNORE INTO user 
           (id, name, email, role, profile_image_url, created_at, updated_at, last_active_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, "System", "system@mai.local", "admin", "/user.png", timestamp, timestamp, timestamp)
    )
    return user_id

def register_models(db_path="/app/backend/data/webui.db", dry_run=False):
    """Register OpenRouter models in the database."""
    print(f"{'DRY RUN: ' if dry_run else ''}Registering OpenRouter models...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get admin user ID
        admin_id = get_admin_user_id(cursor)
        print(f"Using admin user ID: {admin_id}")
        
        # Check existing models
        cursor.execute("SELECT id FROM model")
        existing_models = set(row[0] for row in cursor.fetchall())
        print(f"Found {len(existing_models)} existing models")
        
        registered = 0
        skipped = 0
        
        for model_info in OPENROUTER_MODELS:
            model_id = model_info["id"]
            
            if model_id in existing_models:
                print(f"  ⏭️  Skipping {model_id} - already exists")
                skipped += 1
                continue
            
            # Prepare model data
            timestamp = int(time.time())
            
            # Model metadata
            meta = {
                "profile_image_url": "/static/favicon.png",
                "description": model_info["description"],
                "capabilities": {
                    "vision": False,  # Could be updated based on actual model capabilities
                    "tools": False
                }
            }
            
            # Model parameters
            params = {
                "provider": "openrouter"
            }
            
            # Access control - NULL means public access for all users
            access_control = None  # Public access
            
            if not dry_run:
                cursor.execute(
                    """INSERT INTO model 
                       (id, user_id, base_model_id, name, params, meta, access_control, is_active, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        model_id,
                        admin_id,
                        None,  # base_model_id - these are base models
                        model_info["name"],
                        json.dumps(params),
                        json.dumps(meta),
                        json.dumps(access_control) if access_control else None,
                        1,  # is_active
                        timestamp,
                        timestamp
                    )
                )
            
            print(f"  ✅ {'Would register' if dry_run else 'Registered'} {model_id} - {model_info['name']}")
            registered += 1
        
        if not dry_run:
            conn.commit()
            
        print(f"\nSummary:")
        print(f"  Models {'would be ' if dry_run else ''}registered: {registered}")
        print(f"  Models skipped (already exist): {skipped}")
        print(f"  Total models in database: {len(existing_models) + registered}")
        
        # Verify registration
        if not dry_run:
            cursor.execute("SELECT COUNT(*) FROM model")
            total = cursor.fetchone()[0]
            print(f"\n✓ Verification: {total} models now in database")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error registering models: {e}")
        return False

def check_bypass_setting(db_path="/app/backend/data/webui.db"):
    """Check if BYPASS_MODEL_ACCESS_CONTROL is enabled."""
    print("\n=== Checking BYPASS_MODEL_ACCESS_CONTROL Setting ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM config ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        if result:
            config_data = json.loads(result[0])
            bypass = config_data.get('features', {}).get('bypass_model_access_control', False)
            print(f"BYPASS_MODEL_ACCESS_CONTROL: {bypass}")
            
            if not bypass:
                print("\n💡 TIP: You can enable BYPASS_MODEL_ACCESS_CONTROL to allow all users")
                print("   to see all models without access control restrictions.")
                print("   This can be done through the admin settings UI.")
        
        conn.close()
    except Exception as e:
        print(f"Error checking config: {e}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Register OpenRouter models in mAI database")
    parser.add_argument("--db", default="/app/backend/data/webui.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--check-only", action="store_true", help="Only check current state, don't register")
    
    args = parser.parse_args()
    
    print("🚀 OpenRouter Model Registration Tool")
    print("=" * 50)
    print(f"Database: {args.db}")
    
    if args.check_only:
        # Just check current state
        try:
            conn = sqlite3.connect(args.db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, access_control FROM model")
            models = cursor.fetchall()
            
            print(f"\nFound {len(models)} models in database:")
            for model in models:
                access = "Private" if model[2] == '{}' else "Public" if model[2] is None else "Custom"
                print(f"  - {model[0]} ({model[1]}) - Access: {access}")
            
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
            
        check_bypass_setting(args.db)
    else:
        # Register models
        if register_models(args.db, dry_run=args.dry_run):
            if not args.dry_run:
                print("\n✅ Models registered successfully!")
                print("\nNext steps:")
                print("1. Restart the mAI application to load the new models")
                print("2. Check that users can now see the models")
                print("3. If users still can't see models, check:")
                print("   - User role is not 'pending'")
                print("   - BYPASS_MODEL_ACCESS_CONTROL setting")
                
                check_bypass_setting(args.db)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()