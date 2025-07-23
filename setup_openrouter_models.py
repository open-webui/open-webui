#!/usr/bin/env python3
"""
Script to configure OpenRouter in Open WebUI with only the 12 specified models.
This script can be used to update the configuration via the API or by modifying the database directly.
"""

import json
import requests
from typing import Dict, List

# The 12 specific models to allow
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

def update_openrouter_config_via_api(
    base_url: str,
    admin_token: str,
    openrouter_api_key: str
) -> None:
    """
    Update Open WebUI configuration to add OpenRouter with model restrictions.
    
    Args:
        base_url: Open WebUI base URL (e.g., "http://localhost:8080")
        admin_token: Admin user's API token
        openrouter_api_key: OpenRouter API key
    """
    
    # First, get current configuration
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    config_response = requests.get(
        f"{base_url}/api/v1/openai/config",
        headers=headers
    )
    
    if config_response.status_code != 200:
        raise Exception(f"Failed to get config: {config_response.text}")
    
    current_config = config_response.json()
    
    # Prepare updated configuration
    openai_base_urls = current_config.get("OPENAI_API_BASE_URLS", [])
    openai_api_keys = current_config.get("OPENAI_API_KEYS", [])
    openai_api_configs = current_config.get("OPENAI_API_CONFIGS", {})
    
    # Add OpenRouter if not already present
    openrouter_url = "https://openrouter.ai/api/v1"
    
    if openrouter_url in openai_base_urls:
        # Update existing configuration
        idx = openai_base_urls.index(openrouter_url)
        openai_api_keys[idx] = openrouter_api_key
    else:
        # Add new configuration
        openai_base_urls.append(openrouter_url)
        openai_api_keys.append(openrouter_api_key)
        idx = len(openai_base_urls) - 1
    
    # Set up the configuration for this connection
    openai_api_configs[str(idx)] = {
        "enable": True,
        "connection_type": "external",
        "model_ids": ALLOWED_MODELS,
        "tags": ["openrouter", "limited"],
        "prefix_id": None
    }
    
    # Update configuration
    update_data = {
        "ENABLE_OPENAI_API": True,
        "OPENAI_API_BASE_URLS": openai_base_urls,
        "OPENAI_API_KEYS": openai_api_keys,
        "OPENAI_API_CONFIGS": openai_api_configs
    }
    
    update_response = requests.post(
        f"{base_url}/api/v1/openai/config/update",
        headers=headers,
        json=update_data
    )
    
    if update_response.status_code != 200:
        raise Exception(f"Failed to update config: {update_response.text}")
    
    print("✅ OpenRouter configuration updated successfully!")
    print(f"✅ Limited to {len(ALLOWED_MODELS)} models")
    print("\n📋 Allowed models:")
    for model in ALLOWED_MODELS:
        print(f"   - {model}")


def generate_env_config() -> str:
    """Generate environment variable configuration for docker-compose."""
    
    config = {
        "0": {  # Assuming OpenRouter is the first (index 0) connection
            "enable": True,
            "connection_type": "external", 
            "model_ids": ALLOWED_MODELS,
            "tags": ["openrouter", "limited"]
        }
    }
    
    return json.dumps(config, separators=(',', ':'))


def print_manual_instructions():
    """Print manual configuration instructions."""
    
    print("\n📖 MANUAL CONFIGURATION INSTRUCTIONS")
    print("=" * 50)
    print("\n1. Via Web UI (Admin Panel):")
    print("   - Go to Admin Settings > Connections")
    print("   - Add OpenRouter connection:")
    print("     - Name: OpenRouter (Limited)")
    print("     - Base URL: https://openrouter.ai/api/v1")
    print("     - API Key: <Your OpenRouter API Key>")
    print("   - In the Model IDs field, add these models one by one:")
    for model in ALLOWED_MODELS:
        print(f"     - {model}")
    
    print("\n2. Via Environment Variables (Docker):")
    print("   Add to your docker-compose.yml:")
    print("   ```yaml")
    print("   environment:")
    print("     - OPENAI_API_BASE_URLS=https://openrouter.ai/api/v1")
    print("     - OPENAI_API_KEYS=<Your OpenRouter API Key>")
    print(f"     - OPENAI_API_CONFIGS='{generate_env_config()}'")
    print("   ```")
    
    print("\n3. For Easy Updates:")
    print("   - You can use wildcard patterns like:")
    print("     - anthropic/* (all Anthropic models)")
    print("     - google/* (all Google models)")
    print("     - openai/* (all OpenAI models)")
    print("   - But for precise control, use exact model IDs as shown above")


if __name__ == "__main__":
    print("🤖 OpenRouter Model Restriction Setup for Open WebUI")
    print("=" * 50)
    
    print("\nThis script helps configure Open WebUI to only show 12 specific models from OpenRouter.")
    
    print("\nOptions:")
    print("1. Update via API (requires admin token)")
    print("2. Show manual configuration instructions")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        base_url = input("Open WebUI base URL (e.g., http://localhost:8080): ").strip()
        admin_token = input("Admin API token: ").strip()
        openrouter_key = input("OpenRouter API key: ").strip()
        
        try:
            update_openrouter_config_via_api(base_url, admin_token, openrouter_key)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nShowing manual instructions instead...")
            print_manual_instructions()
    else:
        print_manual_instructions()