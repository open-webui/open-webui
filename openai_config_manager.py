"""
OpenAI Configuration Management Module

This module provides a simple API for managing OpenAI configurations
in Open WebUI programmatically.

Example usage:
    from openai_config_manager import OpenAIConfigManager

    # Initialize the manager
    manager = OpenAIConfigManager()

    # List configurations
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

    # Update a configuration
    manager.update(
        config_id='0',
        name='OpenAI GPT-4 Turbo',
        model='gpt-4-turbo'
    )

    # Remove a configuration
    manager.remove('0')

    # Get a specific configuration
    config = manager.get('0')
    print(config)
"""

import sys
from pathlib import Path
from typing import Dict, Optional, List

# Add the backend directory to the Python path
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from open_webui.config import get_config, save_config


class OpenAIConfigManager:
    """Manager class for OpenAI configurations in Open WebUI"""

    def __init__(self):
        """Initialize the configuration manager"""
        self._ensure_config_structure()

    def _ensure_config_structure(self):
        """Ensure the OpenAI configuration structure exists"""
        config = get_config()
        if 'openai' not in config:
            config['openai'] = {
                'enable': True,
                'api_keys': [],
                'api_base_urls': [],
                'api_configs': {}
            }
            save_config(config)

    def _get_openai_config(self) -> dict:
        """Get the OpenAI section of the configuration"""
        config = get_config()
        return config.get('openai', {})

    def _ensure_array_length(self, array: list, index: int, default='') -> list:
        """Ensure array is long enough for the given index"""
        while len(array) <= index:
            array.append(default)
        return array

    def list(self) -> Dict[str, dict]:
        """
        List all OpenAI configurations

        Returns:
            Dictionary mapping config IDs to their configuration data
        """
        openai_config = self._get_openai_config()
        return openai_config.get('api_configs', {})

    def get(self, config_id: str) -> Optional[dict]:
        """
        Get a specific OpenAI configuration

        Args:
            config_id: The configuration ID to retrieve

        Returns:
            Configuration dictionary or None if not found
        """
        configs = self.list()
        config_data = configs.get(config_id)

        if config_data:
            # Include URL and key information
            openai_config = self._get_openai_config()
            idx = int(config_id) if config_id.isdigit() else -1

            result = config_data.copy()

            if idx >= 0:
                base_urls = openai_config.get('api_base_urls', [])
                if idx < len(base_urls):
                    result['base_url'] = base_urls[idx]

                api_keys = openai_config.get('api_keys', [])
                if idx < len(api_keys):
                    result['api_key'] = api_keys[idx]

            return result

        return None

    def add(self, config_id: str, name: str, base_url: Optional[str] = None,
            api_key: Optional[str] = None, **kwargs) -> bool:
        """
        Add a new OpenAI configuration

        Args:
            config_id: The configuration ID (must be numeric)
            name: The configuration name
            base_url: The API base URL (default: https://api.openai.com/v1)
            api_key: The API key
            **kwargs: Additional configuration parameters

        Returns:
            True if successful, False otherwise
        """
        config = get_config()

        # Ensure structure exists
        if 'openai' not in config:
            config['openai'] = {
                'enable': True,
                'api_keys': [],
                'api_base_urls': [],
                'api_configs': {}
            }

        openai_config = config['openai']

        # Check if config already exists
        if config_id in openai_config['api_configs']:
            raise ValueError(f"Configuration with ID '{config_id}' already exists")

        # Validate config_id is numeric
        try:
            idx = int(config_id)
        except ValueError:
            raise ValueError(f"Configuration ID must be a number, got: {config_id}")

        # Ensure arrays exist
        if 'api_base_urls' not in openai_config:
            openai_config['api_base_urls'] = []
        if 'api_keys' not in openai_config:
            openai_config['api_keys'] = []

        # Ensure arrays are long enough
        self._ensure_array_length(openai_config['api_base_urls'], idx)
        self._ensure_array_length(openai_config['api_keys'], idx)

        # Set base URL and API key
        openai_config['api_base_urls'][idx] = base_url or 'https://api.openai.com/v1'
        openai_config['api_keys'][idx] = api_key or ''

        # Create config data
        config_data = {'name': name}
        config_data.update(kwargs)

        openai_config['api_configs'][config_id] = config_data

        # Save configuration
        return save_config(config)

    def update(self, config_id: str, name: Optional[str] = None,
               base_url: Optional[str] = None, api_key: Optional[str] = None,
               **kwargs) -> bool:
        """
        Update an existing OpenAI configuration

        Args:
            config_id: The configuration ID to update
            name: The configuration name (optional)
            base_url: The API base URL (optional)
            api_key: The API key (optional)
            **kwargs: Additional configuration parameters to update

        Returns:
            True if successful, False otherwise
        """
        config = get_config()
        openai_config = config.get('openai', {})

        # Check if config exists
        if config_id not in openai_config.get('api_configs', {}):
            raise ValueError(f"Configuration with ID '{config_id}' not found")

        try:
            idx = int(config_id)
        except ValueError:
            raise ValueError(f"Configuration ID must be a number, got: {config_id}")

        # Ensure arrays are long enough
        if 'api_base_urls' not in openai_config:
            openai_config['api_base_urls'] = []
        if 'api_keys' not in openai_config:
            openai_config['api_keys'] = []

        self._ensure_array_length(openai_config['api_base_urls'], idx)
        self._ensure_array_length(openai_config['api_keys'], idx)

        # Update base URL and API key if provided
        if base_url is not None:
            openai_config['api_base_urls'][idx] = base_url

        if api_key is not None:
            openai_config['api_keys'][idx] = api_key

        # Update config data
        config_data = openai_config['api_configs'][config_id]

        if name is not None:
            config_data['name'] = name

        # Update additional parameters
        config_data.update(kwargs)

        # Save configuration
        return save_config(config)

    def remove(self, config_id: str) -> bool:
        """
        Remove an OpenAI configuration

        Args:
            config_id: The configuration ID to remove

        Returns:
            True if successful, False otherwise
        """
        config = get_config()
        openai_config = config.get('openai', {})

        if config_id not in openai_config.get('api_configs', {}):
            raise ValueError(f"Configuration with ID '{config_id}' not found")

        # Remove the config
        del openai_config['api_configs'][config_id]

        # Clean up the arrays (set to empty string)
        try:
            idx = int(config_id)
            if 'api_base_urls' in openai_config and idx < len(openai_config['api_base_urls']):
                openai_config['api_base_urls'][idx] = ''
            if 'api_keys' in openai_config and idx < len(openai_config['api_keys']):
                openai_config['api_keys'][idx] = ''
        except ValueError:
            pass

        # Save configuration
        return save_config(config)

    def get_all_details(self) -> Dict[str, dict]:
        """
        Get all OpenAI configurations with full details including URLs and keys

        Returns:
            Dictionary mapping config IDs to their full configuration data
        """
        openai_config = self._get_openai_config()
        configs = openai_config.get('api_configs', {})
        base_urls = openai_config.get('api_base_urls', [])
        api_keys = openai_config.get('api_keys', [])

        result = {}
        for config_id, config_data in configs.items():
            full_config = config_data.copy()

            try:
                idx = int(config_id)
                if idx < len(base_urls):
                    full_config['base_url'] = base_urls[idx]
                if idx < len(api_keys):
                    full_config['api_key'] = api_keys[idx]
            except ValueError:
                pass

            result[config_id] = full_config

        return result

    def enable_openai_api(self, enabled: bool = True) -> bool:
        """
        Enable or disable the OpenAI API

        Args:
            enabled: True to enable, False to disable

        Returns:
            True if successful, False otherwise
        """
        config = get_config()
        if 'openai' not in config:
            config['openai'] = {}

        config['openai']['enable'] = enabled
        return save_config(config)

    def is_openai_api_enabled(self) -> bool:
        """
        Check if the OpenAI API is enabled

        Returns:
            True if enabled, False otherwise
        """
        openai_config = self._get_openai_config()
        return openai_config.get('enable', False)


# Example usage
if __name__ == '__main__':
    # Create a manager instance
    manager = OpenAIConfigManager()

    # List all configurations
    print("Current configurations:")
    configs = manager.get_all_details()
    for config_id, config in configs.items():
        print(f"  {config_id}: {config.get('name', 'Unknown')}")

    # Check if OpenAI API is enabled
    print(f"\nOpenAI API enabled: {manager.is_openai_api_enabled()}")

