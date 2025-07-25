#!/usr/bin/env python3
"""
Fix OpenRouter configuration directly in the Docker container database.
"""

import json
import sqlite3

# The 12 models to allow
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

def fix_config():
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    # Get current config
    cursor.execute("SELECT id, data FROM config WHERE id = 1")
    row = cursor.fetchone()
    
    if not row:
        print("❌ No configuration found!")
        return
    
    config_id, config_data = row
    config = json.loads(config_data)
    
    print("📊 Current OpenRouter configuration:")
    print(json.dumps(config.get("openai", {}).get("api_configs", {}), indent=2))
    
    # Check if OpenRouter is configured
    if "openai" not in config:
        print("❌ OpenAI/OpenRouter not configured!")
        return
    
    openai_config = config["openai"]
    api_urls = openai_config.get("api_base_urls", [])
    
    # Find OpenRouter index
    openrouter_idx = None
    for idx, url in enumerate(api_urls):
        if "openrouter.ai" in url:
            openrouter_idx = str(idx)
            print(f"✅ Found OpenRouter at index: {idx}")
            break
    
    if openrouter_idx is None:
        print("❌ OpenRouter URL not found in configuration!")
        return
    
    # Update the configuration
    if "api_configs" not in openai_config:
        openai_config["api_configs"] = {}
    
    openai_config["api_configs"][openrouter_idx] = {
        "enable": True,
        "connection_type": "external",
        "model_ids": ALLOWED_MODELS,
        "tags": ["openrouter", "limited"]
    }
    
    # Save back to database
    cursor.execute(
        "UPDATE config SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(config), config_id)
    )
    
    conn.commit()
    conn.close()
    
    print("\n✅ Configuration updated successfully!")
    print(f"✅ Limited to {len(ALLOWED_MODELS)} models:")
    for model in ALLOWED_MODELS:
        print(f"   - {model}")
    
    print("\n🎯 Next steps:")
    print("1. The backend will reload configuration automatically")
    print("2. Clear your browser cache (Ctrl+Shift+R or Cmd+Shift+R)")
    print("3. Refresh the chat page")
    print("4. Select OpenRouter - you should see only the 12 configured models")

if __name__ == "__main__":
    fix_config()