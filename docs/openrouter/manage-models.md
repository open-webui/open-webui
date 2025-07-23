# Managing OpenRouter Models in mAI

This guide explains how to easily add, remove, or update the OpenRouter model list in your mAI installation.

## Current Model List

Your OpenRouter is currently configured to show only these 12 models:

1. `anthropic/claude-sonnet-4`
2. `google/gemini-2.5-flash`
3. `google/gemini-2.5-pro`
4. `deepseek/deepseek-chat-v3-0324`
5. `anthropic/claude-3.7-sonnet`
6. `google/gemini-2.5-flash-lite-preview-06-17`
7. `openai/gpt-4.1`
8. `x-ai/grok-4`
9. `openai/gpt-4o-mini`
10. `openai/o4-mini-high`
11. `openai/o3`
12. `openai/chatgpt-4o-latest`

## Method 1: Using the Fix Script (Easiest)

### 1. Edit the Model List

Open `fix_openrouter_docker.py` and modify the `ALLOWED_MODELS` list:

```python
# The models to allow
ALLOWED_MODELS = [
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-flash",
    # Add new models here:
    "meta-llama/llama-3.3-70b",
    # Remove models by commenting out or deleting lines
    # "openai/o3",  # Commented out - won't be included
]
```

### 2. Run the Update

```bash
# Copy and run the script in your container
docker cp fix_openrouter_docker.py open-webui-staging:/app/
docker exec open-webui-staging python /app/fix_openrouter_docker.py
```

### 3. Clear Browser Cache

Clear your browser cache and refresh the page to see the changes.

## Method 2: Quick Command Line Update

### Add a Single Model

```bash
docker exec open-webui-staging python -c "
import json, sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT id, data FROM config WHERE id = 1')
config_id, config_data = cursor.fetchone()
config = json.loads(config_data)

# Add new model
config['openai']['api_configs']['0']['model_ids'].append('new-model/name-here')

cursor.execute('UPDATE config SET data = ? WHERE id = ?', (json.dumps(config), config_id))
conn.commit()
conn.close()
print('✅ Model added!')
"
```

### Remove a Model

```bash
docker exec open-webui-staging python -c "
import json, sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT id, data FROM config WHERE id = 1')
config_id, config_data = cursor.fetchone()
config = json.loads(config_data)

# Remove specific model
model_to_remove = 'openai/o3'
if model_to_remove in config['openai']['api_configs']['0']['model_ids']:
    config['openai']['api_configs']['0']['model_ids'].remove(model_to_remove)

cursor.execute('UPDATE config SET data = ? WHERE id = ?', (json.dumps(config), config_id))
conn.commit()
conn.close()
print(f'✅ Model {model_to_remove} removed!')
"
```

## Method 3: Create a Management Script

Save this as `manage_models.py`:

```python
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
```

### Usage Examples:

```bash
# Copy the script
docker cp manage_models.py open-webui-staging:/app/

# List current models
docker exec open-webui-staging python /app/manage_models.py list

# Add a new model
docker exec open-webui-staging python /app/manage_models.py add "anthropic/claude-3-opus"

# Remove a model
docker exec open-webui-staging python /app/manage_models.py remove "openai/o3"

# Replace entire list
docker exec open-webui-staging python /app/manage_models.py set "anthropic/claude-sonnet-4" "google/gemini-2.5-pro" "openai/gpt-4.1"
```

## Method 4: Using Wildcards (Advanced)

Instead of listing each model individually, you can use patterns:

```python
ALLOWED_MODELS = [
    "anthropic/claude-*",     # All Claude models
    "google/gemini-2.5-*",    # All Gemini 2.5 models
    "openai/gpt-4*",          # All GPT-4 variants
    "openai/o*",              # All O-series models
]
```

This requires the wildcard functionality that's already implemented in your backend.

## Important Notes

### After Any Change:

1. **Restart not required** - The configuration is loaded from database on each request
2. **Clear browser cache** - Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
3. **Refresh the chat page** - The model list will update

### Finding Model IDs:

To see all available OpenRouter models and their IDs:
1. Temporarily remove all model restrictions
2. Visit the chat interface
3. Open browser developer tools (F12)
4. Look in the Network tab when selecting models

Or check OpenRouter's documentation at: https://openrouter.ai/models

### Backup Your Configuration:

Before making changes, you can backup:

```bash
# Export current config
docker exec open-webui-staging python -c "
import json, sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT data FROM config WHERE id = 1')
config = json.loads(cursor.fetchone()[0])
print(json.dumps(config['openai']['api_configs']['0'], indent=2))
" > openrouter_config_backup.json
```

## Quick Reference

### Your Current 12 Models:
```python
ALLOWED_MODELS = [
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
]
```

### Common Operations:

```bash
# Check current models
docker exec open-webui-staging python /app/verify_config.py

# Update using fix script
docker cp fix_openrouter_docker.py open-webui-staging:/app/
docker exec open-webui-staging python /app/fix_openrouter_docker.py

# Quick add
docker exec open-webui-staging python /app/manage_models.py add "new-model/id"

# Quick remove
docker exec open-webui-staging python /app/manage_models.py remove "old-model/id"
```

## Troubleshooting

If models don't update:
1. Clear ALL browser data for localhost:3001
2. Try incognito/private mode
3. Check the backend logs: `docker logs open-webui-staging`
4. Verify config: `docker exec open-webui-staging python /app/verify_config.py`