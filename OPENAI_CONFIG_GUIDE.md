# OpenAI Configuration Management Guide

## Overview

This guide explains how to programmatically manage OpenAI configurations in Open WebUI. While you can directly query the database, there's a higher-level abstraction that handles configuration changes properly through the application's configuration system.

## Architecture

### Database Schema
The configuration is stored in the `config` table with the following structure:
- `id`: Integer primary key
- `data`: JSON object containing all configurations
- `version`: Integer version number
- `created_at`: Timestamp
- `updated_at`: Timestamp

### Configuration Path
OpenAI configurations are stored in the JSON data field under the path:
```
data['openai']['api_configs']
```

The structure is:
```json
{
  "openai": {
    "enable": true,
    "api_keys": ["key1", "key2", ...],
    "api_base_urls": ["url1", "url2", ...],
    "api_configs": {
      "0": { "name": "Config 1", ... },
      "1": { "Config 2", ... },
      ...
    }
  }
}
```

## Recommended Approach: Use the Python API

### Method 1: Using the Configuration System (Best Practice)

The configuration system in `backend/open_webui/config.py` provides a high-level API:

```python
from open_webui.config import AppConfig, save_config, get_config

# Get current configuration
config_data = get_config()

# Modify OpenAI API configs
if 'openai' not in config_data:
    config_data['openai'] = {}
if 'api_configs' not in config_data['openai']:
    config_data['openai']['api_configs'] = {}

# Add a new OpenAI configuration
config_data['openai']['api_configs']['0'] = {
    'name': 'My OpenAI Config',
    'model': 'gpt-4',
    'api_key': 'your-api-key',
    'base_url': 'https://api.openai.com/v1'
}

# Save the configuration
save_config(config_data)
```

### Method 2: Using the FastAPI Endpoints

The application exposes REST endpoints for configuration management:

#### Get Current Configuration
```bash
curl -X GET http://localhost:8080/api/openai/config \
  -H "Authorization: Bearer <admin_token>"
```

Response:
```json
{
  "ENABLE_OPENAI_API": true,
  "OPENAI_API_BASE_URLS": ["https://api.openai.com/v1"],
  "OPENAI_API_KEYS": ["sk-..."],
  "OPENAI_API_CONFIGS": {
    "0": {
      "name": "OpenAI Default"
    }
  }
}
```

#### Update Configuration
```bash
curl -X POST http://localhost:8080/api/openai/config/update \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ENABLE_OPENAI_API": true,
    "OPENAI_API_BASE_URLS": ["https://api.openai.com/v1", "https://custom-api.com"],
    "OPENAI_API_KEYS": ["sk-key1", "sk-key2"],
    "OPENAI_API_CONFIGS": {
      "0": {
        "name": "OpenAI Official",
        "model": "gpt-4"
      },
      "1": {
        "name": "Custom Provider",
        "model": "custom-model"
      }
    }
  }'
```

### Method 3: Direct Python Script with App Context

Create a script that uses the application's database session:

```python
#!/usr/bin/env python3
"""
Script to add/remove OpenAI configurations programmatically
"""
import json
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from open_webui.config import get_config, save_config


def add_openai_config(config_id: str, config_data: dict):
    """Add a new OpenAI configuration"""
    config = get_config()
    
    # Initialize structure if it doesn't exist
    if 'openai' not in config:
        config['openai'] = {}
    if 'api_configs' not in config['openai']:
        config['openai']['api_configs'] = {}
    
    # Add the configuration
    config['openai']['api_configs'][config_id] = config_data
    
    # Also ensure we have matching URLs and keys
    if 'api_base_urls' not in config['openai']:
        config['openai']['api_base_urls'] = []
    if 'api_keys' not in config['openai']:
        config['openai']['api_keys'] = []
    
    # Extend arrays to match the config_id index
    idx = int(config_id)
    while len(config['openai']['api_base_urls']) <= idx:
        config['openai']['api_base_urls'].append('')
    while len(config['openai']['api_keys']) <= idx:
        config['openai']['api_keys'].append('')
    
    # Set the URL and key if provided
    if 'base_url' in config_data:
        config['openai']['api_base_urls'][idx] = config_data['base_url']
    if 'api_key' in config_data:
        config['openai']['api_keys'][idx] = config_data['api_key']
    
    # Save configuration
    save_config(config)
    print(f"✓ Added OpenAI config '{config_id}'")


def remove_openai_config(config_id: str):
    """Remove an OpenAI configuration"""
    config = get_config()
    
    if 'openai' not in config or 'api_configs' not in config['openai']:
        print(f"✗ No OpenAI configs found")
        return
    
    if config_id in config['openai']['api_configs']:
        del config['openai']['api_configs'][config_id]
        save_config(config)
        print(f"✓ Removed OpenAI config '{config_id}'")
    else:
        print(f"✗ OpenAI config '{config_id}' not found")


def list_openai_configs():
    """List all OpenAI configurations"""
    config = get_config()
    
    if 'openai' not in config or 'api_configs' not in config['openai']:
        print("No OpenAI configs found")
        return
    
    configs = config['openai']['api_configs']
    print(f"Found {len(configs)} OpenAI configuration(s):")
    print(json.dumps(configs, indent=2))


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage OpenAI configurations')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    subparsers.add_parser('list', help='List all OpenAI configurations')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new OpenAI configuration')
    add_parser.add_argument('id', help='Configuration ID (e.g., 0, 1, 2)')
    add_parser.add_argument('--name', required=True, help='Configuration name')
    add_parser.add_argument('--base-url', default='https://api.openai.com/v1', help='API base URL')
    add_parser.add_argument('--api-key', help='API key')
    add_parser.add_argument('--model', help='Default model')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an OpenAI configuration')
    remove_parser.add_argument('id', help='Configuration ID to remove')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_openai_configs()
    elif args.command == 'add':
        config_data = {'name': args.name}
        if args.base_url:
            config_data['base_url'] = args.base_url
        if args.api_key:
            config_data['api_key'] = args.api_key
        if args.model:
            config_data['model'] = args.model
        add_openai_config(args.id, config_data)
    elif args.command == 'remove':
        remove_openai_config(args.id)
    else:
        parser.print_help()
```

Save this as `manage_openai_config.py` and use it like:

```bash
# List all configs
python manage_openai_config.py list

# Add a new config
python manage_openai_config.py add 0 \
  --name "OpenAI Official" \
  --api-key "sk-..." \
  --model "gpt-4"

# Remove a config
python manage_openai_config.py remove 0
```

## Important Notes

### Configuration Keys Structure
The `OPENAI_API_CONFIGS` dictionary uses string keys (e.g., "0", "1", "2") that correspond to the index in the `OPENAI_API_BASE_URLS` and `OPENAI_API_KEYS` arrays.

### Persistence Mechanism
- The configuration system uses `PersistentConfig` objects that automatically save to the database
- If Redis is configured, configuration changes are also broadcast to all instances
- The system maintains backward compatibility with environment variables

### Security Considerations
1. **Admin Access Required**: Configuration endpoints require admin authentication
2. **API Keys**: Store API keys securely; they're encrypted in the database
3. **Validation**: The update endpoint validates that URLs and keys arrays match in length

### Schema Stability
The configuration system is designed to be backward compatible. New fields can be added to the `api_configs` objects without breaking existing functionality. The application code references:
- `backend/open_webui/routers/openai.py` - OpenAI API endpoints
- `backend/open_webui/config.py` - Configuration persistence layer

## Advantages Over Direct Database Access

1. **Validation**: The configuration API validates inputs and maintains consistency
2. **Notifications**: Changes are broadcast to all running instances (if using Redis)
3. **Backward Compatibility**: Handles migration from old config formats
4. **Type Safety**: Uses Pydantic models for validation
5. **Error Handling**: Proper error messages and rollback on failure
6. **Schema Evolution**: Handles configuration schema changes gracefully

## Example: Complete Configuration Update

```python
from open_webui.config import get_config, save_config

config = get_config()

# Initialize OpenAI section
if 'openai' not in config:
    config['openai'] = {
        'enable': True,
        'api_keys': [],
        'api_base_urls': [],
        'api_configs': {}
    }

# Add multiple OpenAI providers
providers = [
    {
        'id': '0',
        'name': 'OpenAI Official',
        'base_url': 'https://api.openai.com/v1',
        'api_key': 'sk-your-openai-key',
        'model': 'gpt-4'
    },
    {
        'id': '1',
        'name': 'Azure OpenAI',
        'base_url': 'https://your-resource.openai.azure.com',
        'api_key': 'your-azure-key',
        'model': 'gpt-4-32k'
    }
]

for provider in providers:
    idx = int(provider['id'])
    
    # Ensure arrays are long enough
    while len(config['openai']['api_base_urls']) <= idx:
        config['openai']['api_base_urls'].append('')
    while len(config['openai']['api_keys']) <= idx:
        config['openai']['api_keys'].append('')
    
    # Set values
    config['openai']['api_base_urls'][idx] = provider['base_url']
    config['openai']['api_keys'][idx] = provider['api_key']
    config['openai']['api_configs'][provider['id']] = {
        'name': provider['name'],
        'model': provider.get('model', '')
    }

# Save
save_config(config)
print("✓ Configuration saved successfully")
```

## Troubleshooting

### Configuration Not Persisting
- Ensure the database is writable
- Check that `ENABLE_PERSISTENT_CONFIG` environment variable is not set to `False`
- Verify the application has write permissions to the data directory

### Changes Not Reflected in UI
- Clear browser cache
- Check if Redis is configured and working (for multi-instance deployments)
- Restart the application to reload configuration

### Direct Database Queries
If you must query the database directly:
```sql
-- View current config
SELECT data FROM config ORDER BY id DESC LIMIT 1;

-- View OpenAI configs specifically
SELECT json_extract(data, '$.openai.api_configs') as openai_configs 
FROM config 
ORDER BY id DESC 
LIMIT 1;
```

However, always prefer using the Python API or REST endpoints to avoid schema inconsistencies.

