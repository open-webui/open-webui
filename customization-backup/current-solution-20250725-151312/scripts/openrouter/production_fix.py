#!/usr/bin/env python3
"""
Production-ready OpenRouter configuration manager for mAI.
Uses Open WebUI's internal configuration system for persistence.
"""

import json
import sqlite3
import sys
import os
from typing import List, Optional

class ProductionOpenRouterManager:
    """Manages OpenRouter model configuration in production environments."""
    
    # Default models if none specified
    DEFAULT_MODELS = [
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
    
    def __init__(self, db_path: str = '/app/backend/data/webui.db'):
        """Initialize with database path."""
        self.db_path = db_path
        
    def get_models_from_env(self) -> Optional[List[str]]:
        """Get models from environment variable if set."""
        env_models = os.environ.get('OPENROUTER_ALLOWED_MODELS', '')
        if env_models:
            return [m.strip() for m in env_models.split(',') if m.strip()]
        return None
    
    def initialize_config(self) -> bool:
        """Initialize OpenRouter configuration from environment or defaults."""
        models = self.get_models_from_env() or self.DEFAULT_MODELS
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current config
            cursor.execute('SELECT id, data FROM config WHERE id = 1')
            result = cursor.fetchone()
            
            if not result:
                print("❌ No configuration found in database!")
                return False
            
            config_id, config_data = result
            config = json.loads(config_data)
            
            # Ensure OpenAI config exists
            if 'openai' not in config:
                config['openai'] = {
                    'api_base_urls': [],
                    'api_keys': [],
                    'api_configs': {}
                }
            
            openai_config = config['openai']
            api_urls = openai_config.get('api_base_urls', [])
            
            # Find or create OpenRouter entry
            openrouter_idx = None
            for idx, url in enumerate(api_urls):
                if 'openrouter.ai' in url:
                    openrouter_idx = str(idx)
                    break
            
            if openrouter_idx is None:
                # Add OpenRouter if not found
                api_urls.append('https://openrouter.ai/api/v1')
                openai_config['api_base_urls'] = api_urls
                openrouter_idx = str(len(api_urls) - 1)
                
                # Add empty API key placeholder
                api_keys = openai_config.get('api_keys', [])
                api_keys.append('')  # User will add their key via UI
                openai_config['api_keys'] = api_keys
            
            # Configure model restrictions
            if 'api_configs' not in openai_config:
                openai_config['api_configs'] = {}
            
            openai_config['api_configs'][openrouter_idx] = {
                'enable': True,
                'connection_type': 'external',
                'model_ids': models,
                'tags': ['openrouter', 'production', 'managed']
            }
            
            # Save configuration
            cursor.execute(
                'UPDATE config SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (json.dumps(config), config_id)
            )
            
            conn.commit()
            conn.close()
            
            print(f"✅ OpenRouter configuration initialized with {len(models)} models")
            print("\n📋 Configured models:")
            for model in models:
                print(f"   - {model}")
            
            print("\n🔧 Next steps:")
            print("1. Users need to add their OpenRouter API key in Settings → Connections")
            print("2. Model list can be updated via Admin Panel")
            print("3. Or by setting OPENROUTER_ALLOWED_MODELS environment variable")
            
            return True
            
        except Exception as e:
            print(f"❌ Error initializing configuration: {e}")
            return False
    
    def verify_config(self) -> bool:
        """Verify current configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT data FROM config WHERE id = 1')
            config = json.loads(cursor.fetchone()[0])
            
            openai_config = config.get('openai', {})
            api_urls = openai_config.get('api_base_urls', [])
            
            # Find OpenRouter
            for idx, url in enumerate(api_urls):
                if 'openrouter.ai' in url:
                    api_config = openai_config.get('api_configs', {}).get(str(idx), {})
                    models = api_config.get('model_ids', [])
                    
                    print("✅ OpenRouter Configuration Found:")
                    print(f"   URL: {url}")
                    print(f"   Enabled: {api_config.get('enable', False)}")
                    print(f"   Models: {len(models)}")
                    print(f"   Tags: {api_config.get('tags', [])}")
                    
                    if models:
                        print("\n📋 Allowed models:")
                        for model in models:
                            print(f"   - {model}")
                    
                    conn.close()
                    return True
            
            print("❌ OpenRouter configuration not found!")
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ Error verifying configuration: {e}")
            return False

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python openrouter_production_fix.py [init|verify]")
        print("\nCommands:")
        print("  init    - Initialize OpenRouter configuration")
        print("  verify  - Verify current configuration")
        print("\nEnvironment variables:")
        print("  OPENROUTER_ALLOWED_MODELS - Comma-separated list of model IDs")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = ProductionOpenRouterManager()
    
    if command == "init":
        manager.initialize_config()
    elif command == "verify":
        manager.verify_config()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()