#!/usr/bin/env python3
"""
Script to add/remove OpenAI configurations programmatically in Open WebUI.

This script uses the Open WebUI configuration system to safely modify
OpenAI configurations without directly manipulating the database.

Usage:
    # List all configurations
    python manage_openai_config.py list

    # Add a new configuration
    python manage_openai_config.py add 0 \
        --name "OpenAI Official" \
        --base-url "https://api.openai.com/v1" \
        --api-key "sk-..." \
        --model "gpt-4"

    # Update an existing configuration
    python manage_openai_config.py update 0 \
        --name "OpenAI GPT-4 Turbo" \
        --model "gpt-4-turbo"

    # Remove a configuration
    python manage_openai_config.py remove 0

    # Export configurations to JSON
    python manage_openai_config.py export > openai_configs.json

    # Import configurations from JSON
    python manage_openai_config.py import < openai_configs.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add the backend directory to the Python path
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from open_webui.config import get_config, save_config
except ImportError as e:
    print(f"Error: Could not import Open WebUI modules. Make sure this script is in the Open WebUI root directory.")
    print(f"Details: {e}")
    sys.exit(1)


def get_openai_section(config: dict) -> dict:
    """Get or initialize the OpenAI section of the config"""
    if 'openai' not in config:
        config['openai'] = {
            'enable': True,
            'api_keys': [],
            'api_base_urls': [],
            'api_configs': {}
        }

    if 'api_configs' not in config['openai']:
        config['openai']['api_configs'] = {}
    if 'api_base_urls' not in config['openai']:
        config['openai']['api_base_urls'] = []
    if 'api_keys' not in config['openai']:
        config['openai']['api_keys'] = []

    return config['openai']


def ensure_array_length(array: list, index: int, default='') -> list:
    """Ensure array is long enough for the given index"""
    while len(array) <= index:
        array.append(default)
    return array


def list_configs():
    """List all OpenAI configurations"""
    config = get_config()
    openai_config = config.get('openai', {})

    if not openai_config or 'api_configs' not in openai_config or not openai_config['api_configs']:
        print("No OpenAI configurations found.")
        return

    configs = openai_config['api_configs']
    base_urls = openai_config.get('api_base_urls', [])
    api_keys = openai_config.get('api_keys', [])

    print(f"Found {len(configs)} OpenAI configuration(s):\n")

    for config_id in sorted(configs.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
        config_data = configs[config_id]
        idx = int(config_id) if config_id.isdigit() else -1

        print(f"ID: {config_id}")
        print(f"  Name: {config_data.get('name', 'N/A')}")

        if idx >= 0 and idx < len(base_urls):
            print(f"  Base URL: {base_urls[idx]}")

        if idx >= 0 and idx < len(api_keys):
            key = api_keys[idx]
            if key:
                masked_key = key[:8] + '...' + key[-4:] if len(key) > 12 else '***'
                print(f"  API Key: {masked_key}")

        for key, value in config_data.items():
            if key not in ['name', 'base_url', 'api_key']:
                print(f"  {key}: {value}")
        print()


def add_config(config_id: str, name: str, base_url: Optional[str] = None,
               api_key: Optional[str] = None, model: Optional[str] = None,
               **kwargs):
    """Add a new OpenAI configuration"""
    config = get_config()
    openai_config = get_openai_section(config)

    # Check if config already exists
    if config_id in openai_config['api_configs']:
        print(f"✗ Configuration with ID '{config_id}' already exists. Use 'update' command to modify it.")
        return False

    # Validate config_id is numeric
    try:
        idx = int(config_id)
    except ValueError:
        print(f"✗ Configuration ID must be a number, got: {config_id}")
        return False

    # Ensure arrays are long enough
    ensure_array_length(openai_config['api_base_urls'], idx)
    ensure_array_length(openai_config['api_keys'], idx)

    # Set base URL and API key
    if base_url:
        openai_config['api_base_urls'][idx] = base_url
    else:
        openai_config['api_base_urls'][idx] = 'https://api.openai.com/v1'

    if api_key:
        openai_config['api_keys'][idx] = api_key

    # Create config data
    config_data = {'name': name}
    if model:
        config_data['model'] = model

    # Add any additional kwargs
    config_data.update(kwargs)

    openai_config['api_configs'][config_id] = config_data

    # Save configuration
    if save_config(config):
        print(f"✓ Added OpenAI configuration '{config_id}' ({name})")
        return True
    else:
        print(f"✗ Failed to save configuration")
        return False


def update_config(config_id: str, name: Optional[str] = None,
                  base_url: Optional[str] = None, api_key: Optional[str] = None,
                  model: Optional[str] = None, **kwargs):
    """Update an existing OpenAI configuration"""
    config = get_config()
    openai_config = get_openai_section(config)

    # Check if config exists
    if config_id not in openai_config['api_configs']:
        print(f"✗ Configuration with ID '{config_id}' not found. Use 'add' command to create it.")
        return False

    try:
        idx = int(config_id)
    except ValueError:
        print(f"✗ Configuration ID must be a number, got: {config_id}")
        return False

    # Ensure arrays are long enough
    ensure_array_length(openai_config['api_base_urls'], idx)
    ensure_array_length(openai_config['api_keys'], idx)

    # Update base URL and API key if provided
    if base_url is not None:
        openai_config['api_base_urls'][idx] = base_url

    if api_key is not None:
        openai_config['api_keys'][idx] = api_key

    # Update config data
    config_data = openai_config['api_configs'][config_id]

    if name is not None:
        config_data['name'] = name
    if model is not None:
        config_data['model'] = model

    # Update any additional kwargs
    config_data.update(kwargs)

    # Save configuration
    if save_config(config):
        print(f"✓ Updated OpenAI configuration '{config_id}'")
        return True
    else:
        print(f"✗ Failed to save configuration")
        return False


def remove_config(config_id: str):
    """Remove an OpenAI configuration"""
    config = get_config()
    openai_config = get_openai_section(config)

    if config_id not in openai_config['api_configs']:
        print(f"✗ Configuration with ID '{config_id}' not found")
        return False

    # Remove the config
    config_name = openai_config['api_configs'][config_id].get('name', config_id)
    del openai_config['api_configs'][config_id]

    # Optionally clean up the arrays (set to empty string instead of removing to preserve indices)
    try:
        idx = int(config_id)
        if idx < len(openai_config['api_base_urls']):
            openai_config['api_base_urls'][idx] = ''
        if idx < len(openai_config['api_keys']):
            openai_config['api_keys'][idx] = ''
    except ValueError:
        pass

    # Save configuration
    if save_config(config):
        print(f"✓ Removed OpenAI configuration '{config_id}' ({config_name})")
        return True
    else:
        print(f"✗ Failed to save configuration")
        return False


def export_configs():
    """Export all OpenAI configurations to JSON"""
    config = get_config()
    openai_config = config.get('openai', {})

    if not openai_config:
        print("{}", file=sys.stdout)
        return

    # Export the entire openai section
    print(json.dumps(openai_config, indent=2))


def import_configs():
    """Import OpenAI configurations from JSON (stdin)"""
    try:
        import_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON input: {e}", file=sys.stderr)
        return False

    config = get_config()

    # Validate the structure
    if not isinstance(import_data, dict):
        print(f"✗ Invalid format: expected a JSON object", file=sys.stderr)
        return False

    # Replace or merge the openai section
    config['openai'] = import_data

    # Save configuration
    if save_config(config):
        configs_count = len(import_data.get('api_configs', {}))
        print(f"✓ Imported {configs_count} OpenAI configuration(s)")
        return True
    else:
        print(f"✗ Failed to save configuration")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Manage OpenAI configurations in Open WebUI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all OpenAI configurations')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new OpenAI configuration')
    add_parser.add_argument('id', help='Configuration ID (numeric, e.g., 0, 1, 2)')
    add_parser.add_argument('--name', required=True, help='Configuration name')
    add_parser.add_argument('--base-url', help='API base URL (default: https://api.openai.com/v1)')
    add_parser.add_argument('--api-key', help='API key')
    add_parser.add_argument('--model', help='Default model')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing OpenAI configuration')
    update_parser.add_argument('id', help='Configuration ID to update')
    update_parser.add_argument('--name', help='Configuration name')
    update_parser.add_argument('--base-url', help='API base URL')
    update_parser.add_argument('--api-key', help='API key')
    update_parser.add_argument('--model', help='Default model')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an OpenAI configuration')
    remove_parser.add_argument('id', help='Configuration ID to remove')

    # Export command
    subparsers.add_parser('export', help='Export all OpenAI configurations to JSON (stdout)')

    # Import command
    subparsers.add_parser('import', help='Import OpenAI configurations from JSON (stdin)')

    args = parser.parse_args()

    if args.command == 'list':
        list_configs()
    elif args.command == 'add':
        add_config(
            args.id,
            args.name,
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model
        )
    elif args.command == 'update':
        update_config(
            args.id,
            name=args.name,
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model
        )
    elif args.command == 'remove':
        remove_config(args.id)
    elif args.command == 'export':
        export_configs()
    elif args.command == 'import':
        import_configs()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

