# OpenAI Configuration Management Tools

This directory contains tools and documentation for programmatically managing OpenAI configurations in Open WebUI.

## Files

- **OPENAI_CONFIG_GUIDE.md** - Complete guide explaining the configuration architecture and various approaches
- **manage_openai_config.py** - Command-line tool for managing configurations
- **openai_config_manager.py** - Python module for programmatic configuration management

## Quick Start

### Using the Command-Line Tool

```bash
# List all OpenAI configurations
python manage_openai_config.py list

# Add a new configuration
python manage_openai_config.py add 0 \
    --name "OpenAI Official" \
    --base-url "https://api.openai.com/v1" \
    --api-key "sk-your-key" \
    --model "gpt-4"

# Update a configuration
python manage_openai_config.py update 0 \
    --name "OpenAI GPT-4 Turbo" \
    --model "gpt-4-turbo"

# Remove a configuration
python manage_openai_config.py remove 0

# Export all configurations
python manage_openai_config.py export > openai_configs.json

# Import configurations
python manage_openai_config.py import < openai_configs.json
```

### Using the Python Module

```python
from openai_config_manager import OpenAIConfigManager

# Create a manager instance
manager = OpenAIConfigManager()

# List all configurations
configs = manager.list()
print(configs)

# Add a configuration
manager.add(
    config_id='0',
    name='OpenAI Official',
    base_url='https://api.openai.com/v1',
    api_key='sk-...',
    model='gpt-4'
)

# Get a specific configuration
config = manager.get('0')
print(config)

# Update a configuration
manager.update(
    config_id='0',
    name='OpenAI GPT-4 Turbo',
    model='gpt-4-turbo'
)

# Remove a configuration
manager.remove('0')

# Get all configurations with full details
all_configs = manager.get_all_details()
for config_id, config in all_configs.items():
    print(f"{config_id}: {config['name']}")

# Enable/disable OpenAI API
manager.enable_openai_api(True)
```

### Using the REST API

```bash
# Get current configuration
curl -X GET http://localhost:8080/api/openai/config \
  -H "Authorization: Bearer <admin_token>"

# Update configuration
curl -X POST http://localhost:8080/api/openai/config/update \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ENABLE_OPENAI_API": true,
    "OPENAI_API_BASE_URLS": ["https://api.openai.com/v1"],
    "OPENAI_API_KEYS": ["sk-..."],
    "OPENAI_API_CONFIGS": {
      "0": {
        "name": "OpenAI Official",
        "model": "gpt-4"
      }
    }
  }'
```

## Configuration Structure

OpenAI configurations are stored in the database under the path `data['openai']` with the following structure:

```json
{
  "openai": {
    "enable": true,
    "api_keys": ["key1", "key2"],
    "api_base_urls": ["url1", "url2"],
    "api_configs": {
      "0": {
        "name": "Configuration 1",
        "model": "gpt-4"
      },
      "1": {
        "name": "Configuration 2",
        "model": "gpt-3.5-turbo"
      }
    }
  }
}
```

The numeric keys in `api_configs` correspond to indices in the `api_keys` and `api_base_urls` arrays.

## Why Use These Tools Instead of Direct Database Access?

1. **Schema Validation** - Ensures configuration structure is valid
2. **Consistency** - Maintains proper alignment between URLs, keys, and configs
3. **Change Propagation** - Updates are broadcast to all running instances (if using Redis)
4. **Error Handling** - Proper validation and error messages
5. **Future-Proof** - Handles schema evolution automatically

## Requirements

- Open WebUI installation
- Python 3.8+
- Admin access (for REST API endpoints)

## Docker Usage

If running Open WebUI in Docker, you can execute the management script inside the container:

```bash
# List configurations
docker exec -it open-webui python manage_openai_config.py list

# Add a configuration
docker exec -it open-webui python manage_openai_config.py add 0 \
    --name "OpenAI" \
    --api-key "sk-..."

# Or copy the script into the container
docker cp manage_openai_config.py open-webui:/app/
docker exec -it open-webui python /app/manage_openai_config.py list
```

## Troubleshooting

### ImportError
Make sure you're running the script from the Open WebUI root directory or that the backend path is correct.

### Permission Errors
Ensure the application has write access to the database and data directory.

### Configuration Not Persisting
- Check that `ENABLE_PERSISTENT_CONFIG` is not set to `False`
- Verify database connectivity
- Check logs for errors during save operations

## Advanced Examples

### Batch Add Multiple Configurations

```python
from openai_config_manager import OpenAIConfigManager

manager = OpenAIConfigManager()

providers = [
    {
        'id': '0',
        'name': 'OpenAI Official',
        'base_url': 'https://api.openai.com/v1',
        'api_key': 'sk-...',
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
    try:
        manager.add(
            config_id=provider['id'],
            name=provider['name'],
            base_url=provider['base_url'],
            api_key=provider['api_key'],
            model=provider['model']
        )
        print(f"✓ Added {provider['name']}")
    except ValueError as e:
        print(f"✗ Failed to add {provider['name']}: {e}")
```

### Export and Backup

```bash
# Create a timestamped backup
python manage_openai_config.py export > "openai_config_backup_$(date +%Y%m%d_%H%M%S).json"

# Restore from backup
python manage_openai_config.py import < openai_config_backup_20260217_120000.json
```

## Documentation

For more detailed information, see [OPENAI_CONFIG_GUIDE.md](OPENAI_CONFIG_GUIDE.md).

## Contributing

If you find issues or have suggestions for improvements, please contribute back to the Open WebUI project.

## License

These tools are provided as utilities for Open WebUI and follow the same license as the main project.

