#!/usr/bin/env python3

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.config import get_config, save_config

def add_gpt_4_1_nano_model():
    """Add gpt-4.1-nano model to the OpenAI API configuration."""
    
    # Get current configuration
    config = get_config()
    
    print("Current configuration:")
    print(f"  openai.api_configs: {config.get('openai', {}).get('api_configs', {})}")
    
    # Get or create openai section
    if 'openai' not in config:
        config['openai'] = {}
    
    # Get or create api_configs section
    if 'api_configs' not in config['openai']:
        config['openai']['api_configs'] = {}
    
    # Find the first OpenAI connection (usually index "0")
    # If no connections exist, create one
    if not config['openai']['api_configs']:
        print("No OpenAI API configurations found. Creating default configuration...")
        config['openai']['api_configs']['0'] = {
            'enable': True,
            'model_ids': ['gpt-4.1-nano'],
            'connection_type': 'external'
        }
    else:
        # Add gpt-4.1-nano to the first connection
        first_key = list(config['openai']['api_configs'].keys())[0]
        first_config = config['openai']['api_configs'][first_key]
        
        # Get or create model_ids list
        if 'model_ids' not in first_config:
            first_config['model_ids'] = []
        
        # Add gpt-4.1-nano if not already present
        if 'gpt-4.1-nano' not in first_config['model_ids']:
            first_config['model_ids'].append('gpt-4.1-nano')
            print(f"Added 'gpt-4.1-nano' to connection {first_key}")
        else:
            print("'gpt-4.1-nano' is already in the model_ids list")
    
    # Save the updated configuration
    success = save_config(config)
    
    if success:
        print("\nConfiguration updated successfully!")
        print("Updated configuration:")
        print(f"  openai.api_configs: {config.get('openai', {}).get('api_configs', {})}")
        print("\nYou may need to restart the backend server for changes to take effect.")
    else:
        print("Failed to save configuration!")
        return False
    
    return True

if __name__ == "__main__":
    add_gpt_4_1_nano_model() 