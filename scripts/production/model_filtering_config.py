#!/usr/bin/env python3
"""
Production-ready model filtering configuration for mAI OpenRouter integration.
This script provides centralized management for the 12-model filtering across all client instances.
"""

import json
import os
from typing import Dict, List, Optional

# Production model configuration - centralized and version controlled
PRODUCTION_MODEL_CONFIG = {
    "0": {
        "enable": True,
        "connection_type": "external",
        "model_ids": [
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
        ],
        "tags": ["openrouter"],
        "prefix_id": None
    }
}

def get_model_config_json(compact: bool = True) -> str:
    """
    Get the model configuration as a JSON string for environment variables.
    
    Args:
        compact: If True, returns compact JSON. If False, returns pretty-printed JSON.
        
    Returns:
        JSON string representation of the model configuration
    """
    if compact:
        return json.dumps(PRODUCTION_MODEL_CONFIG, separators=(',', ':'))
    else:
        return json.dumps(PRODUCTION_MODEL_CONFIG, indent=2)

def validate_model_config(config: Dict) -> bool:
    """
    Validate that the model configuration is correct and complete.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Check required structure
        if "0" not in config:
            print("❌ Missing index '0' in configuration")
            return False
            
        config_0 = config["0"]
        
        # Check required fields
        required_fields = ["enable", "connection_type", "model_ids"]
        for field in required_fields:
            if field not in config_0:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate model_ids
        model_ids = config_0["model_ids"]
        if not isinstance(model_ids, list):
            print("❌ model_ids must be a list")
            return False
            
        if len(model_ids) != 12:
            print(f"❌ Expected 12 models, found {len(model_ids)}")
            return False
            
        # Validate each model ID format
        for model_id in model_ids:
            if not isinstance(model_id, str) or "/" not in model_id:
                print(f"❌ Invalid model ID format: {model_id}")
                return False
        
        print("✅ Model configuration validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation error: {e}")
        return False

def get_expected_models() -> List[str]:
    """Get the list of expected model IDs for verification."""
    return PRODUCTION_MODEL_CONFIG["0"]["model_ids"]

def create_env_file_entry() -> str:
    """
    Create the environment file entry for OPENAI_API_CONFIGS.
    
    Returns:
        String to add to .env file
    """
    config_json = get_model_config_json(compact=True)
    return f"OPENAI_API_CONFIGS='{config_json}'"

def print_configuration_summary():
    """Print a summary of the current configuration."""
    print("🔧 mAI OpenRouter Model Filtering Configuration")
    print("=" * 60)
    print(f"📊 Total models configured: {len(PRODUCTION_MODEL_CONFIG['0']['model_ids'])}")
    print(f"🏷️  Connection type: {PRODUCTION_MODEL_CONFIG['0']['connection_type']}")
    print(f"🏃 Enabled: {PRODUCTION_MODEL_CONFIG['0']['enable']}")
    print(f"📋 Tags: {', '.join(PRODUCTION_MODEL_CONFIG['0']['tags'])}")
    print("\n📝 Configured Models:")
    
    for i, model_id in enumerate(PRODUCTION_MODEL_CONFIG['0']['model_ids'], 1):
        provider, model = model_id.split('/', 1)
        print(f"  {i:2d}. {provider:12} | {model}")
    
    print("\n💾 Environment Variable:")
    print(f"OPENAI_API_CONFIGS='{get_model_config_json(compact=True)}'")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage mAI OpenRouter model filtering configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python model_filtering_config.py --summary
  python model_filtering_config.py --env-var
  python model_filtering_config.py --validate-json '{"0":{"enable":true,...}}'
        """
    )
    
    parser.add_argument("--summary", action="store_true", 
                       help="Show configuration summary")
    parser.add_argument("--env-var", action="store_true",
                       help="Output environment variable for .env file")
    parser.add_argument("--json", action="store_true",
                       help="Output configuration as JSON")
    parser.add_argument("--validate-json", type=str,
                       help="Validate a JSON configuration string")
    parser.add_argument("--compact", action="store_true",
                       help="Use compact JSON output")
    
    args = parser.parse_args()
    
    if args.summary:
        print_configuration_summary()
    elif args.env_var:
        print(create_env_file_entry())
    elif args.json:
        print(get_model_config_json(compact=args.compact))
    elif args.validate_json:
        try:
            config = json.loads(args.validate_json)
            validate_model_config(config)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
    else:
        parser.print_help()