#!/usr/bin/env python3
"""
Manage OpenRouter models in mAI
Usage:
  python manage_models.py list
  python manage_models.py add "model/name"
  python manage_models.py remove "model/name"
  python manage_models.py set "model1" "model2" "model3"
"""

import json
import sqlite3
import sys

def get_config():
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, data FROM config WHERE id = 1')
    config_id, config_data = cursor.fetchone()
    config = json.loads(config_data)
    return conn, cursor, config_id, config

def save_config(conn, cursor, config_id, config):
    cursor.execute('UPDATE config SET data = ? WHERE id = ?', (json.dumps(config), config_id))
    conn.commit()
    conn.close()

def list_models():
    conn, cursor, config_id, config = get_config()
    models = config['openai']['api_configs']['0'].get('model_ids', [])
    print(f"📋 Current models ({len(models)}):")
    for i, model in enumerate(models, 1):
        print(f"   {i}. {model}")
    conn.close()

def add_model(model_name):
    conn, cursor, config_id, config = get_config()
    models = config['openai']['api_configs']['0'].get('model_ids', [])
    if model_name not in models:
        models.append(model_name)
        config['openai']['api_configs']['0']['model_ids'] = models
        save_config(conn, cursor, config_id, config)
        print(f"✅ Added: {model_name}")
    else:
        print(f"⚠️  Model already exists: {model_name}")
        conn.close()

def remove_model(model_name):
    conn, cursor, config_id, config = get_config()
    models = config['openai']['api_configs']['0'].get('model_ids', [])
    if model_name in models:
        models.remove(model_name)
        config['openai']['api_configs']['0']['model_ids'] = models
        save_config(conn, cursor, config_id, config)
        print(f"✅ Removed: {model_name}")
    else:
        print(f"⚠️  Model not found: {model_name}")
        conn.close()

def set_models(model_list):
    conn, cursor, config_id, config = get_config()
    config['openai']['api_configs']['0']['model_ids'] = model_list
    save_config(conn, cursor, config_id, config)
    print(f"✅ Set {len(model_list)} models")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_models()
    elif command == "add" and len(sys.argv) > 2:
        add_model(sys.argv[2])
    elif command == "remove" and len(sys.argv) > 2:
        remove_model(sys.argv[2])
    elif command == "set" and len(sys.argv) > 2:
        set_models(sys.argv[2:])
    else:
        print(__doc__)