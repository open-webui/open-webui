#!/usr/bin/env python3
"""
Simple development environment setup for mAI.
This script helps you generate a development API key and create .env.dev
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ requests library is required. Install with: pip install requests")
    sys.exit(1)


def validate_provisioning_key(key):
    """Validate the provisioning key format"""
    if not key.startswith('sk-or-v1-'):
        return False, "Invalid format! Must start with 'sk-or-v1-'"
    
    # OpenRouter provisioning keys are typically 64 characters after the prefix
    if len(key) < 73:  # sk-or-v1- (9 chars) + 64 chars
        return False, "Key appears too short. Please check you copied the entire key."
    
    return True, "Key format valid"


def create_api_key(provisioning_key, org_name):
    """Create a development API key"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {provisioning_key}'
    }
    
    data = {
        'name': f'mAI Dev: {org_name}',
        'label': f'mai-dev-{org_name.lower().replace(" ", "-")}',
        'limit': None  # Optional: set a credit limit if needed
    }
    
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/keys',
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            # The response format is: { "data": {...}, "key": "sk-or-v1-..." }
            api_key = result.get('key')
            key_hash = result.get('data', {}).get('hash')
            if api_key:
                return True, api_key, key_hash
            else:
                return False, None, "No API key returned in response"
        else:
            # Try to get error message from response
            error_msg = f"Status: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error']}"
                elif 'message' in error_data:
                    error_msg += f" - {error_data['message']}"
            except:
                error_msg += f" - {response.text[:200]}"
            return False, None, error_msg
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def test_api_key(api_key, org_name):
    """Test the API key and get external user"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'HTTP-Referer': 'http://localhost:5173',
        'X-Title': f'mAI Dev Test - {org_name}'
    }
    
    data = {
        'model': 'meta-llama/llama-3.2-3b-instruct:free',
        'messages': [{'role': 'user', 'content': 'Hi'}],
        'max_tokens': 1,
        'stream': False
    }
    
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            external_user = None
            
            # Try to get external_user from headers
            if 'x-external-user' in response.headers:
                external_user = response.headers['x-external-user']
            
            return True, external_user
        else:
            return False, None
    except Exception as e:
        print(f"Warning: Test failed ({str(e)}), but continuing...")
        return True, None  # Continue anyway


def generate_external_user(org_name):
    """Generate a fallback external user ID"""
    import hashlib
    import time
    
    # Create a unique identifier
    unique_string = f"{org_name}_{time.time()}"
    hash_object = hashlib.md5(unique_string.encode())
    short_hash = hash_object.hexdigest()[:8]
    
    # Format: mai_dev_<short_hash>
    return f"mai_dev_{short_hash}"


def create_env_dev_file(api_key, org_name, external_user):
    """Create the .env.dev file"""
    
    env_content = f"""# ================================================================
# mAI Development Environment Configuration
# Generated: {datetime.now().isoformat()}
# Organization: {org_name} (DEV)
# ================================================================

# ============= CORE APPLICATION (DEVELOPMENT) =============
ENV=dev
PORT=8080
UVICORN_WORKERS=1

# Development URLs
WEBUI_URL=http://localhost:5173
BACKEND_URL=http://localhost:8080
WEBUI_NAME=mAI Development (BACKEND)
ADMIN_EMAIL=dev@localhost

# Development Secret Key
WEBUI_SECRET_KEY=mai-secret-key-development-2025

# ============= SECURITY (RELAXED FOR DEV) =============
WEBUI_AUTH=True
JWT_EXPIRES_IN=24h
ENABLE_PERSISTENT_CONFIG=True

# HTTP-friendly for localhost
WEBUI_SESSION_COOKIE_SECURE=False
WEBUI_AUTH_COOKIE_SECURE=False
WEBUI_SESSION_COOKIE_SAME_SITE=lax
WEBUI_AUTH_COOKIE_SAME_SITE=lax

# CORS for development
CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:3001

# Development visibility
SHOW_ADMIN_DETAILS=True
ENABLE_VERSION_UPDATE_CHECK=False
RESET_CONFIG_ON_START=False
SAFE_MODE=False

# ============= USER MANAGEMENT (DEV) =============
ENABLE_SIGNUP=True
ENABLE_LOGIN_FORM=True
DEFAULT_USER_ROLE=user
DEFAULT_LOCALE=en

# Admin features
ENABLE_ADMIN_EXPORT=True
ENABLE_ADMIN_CHAT_ACCESS=True

# ============= OPENROUTER CONFIGURATION =============
ENABLE_OPENAI_API=True
OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY={api_key}
OPENROUTER_API_KEY={api_key}
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER={external_user}
ORGANIZATION_NAME={org_name} (DEV)
SPENDING_LIMIT=unlimited
ENABLE_FORWARD_USER_INFO_HEADERS=True

# Model Access Control
ENABLE_MODEL_FILTER=True
BYPASS_MODEL_ACCESS_CONTROL=False

# OpenRouter Model Configuration - Limit to 12 mAI business models
OPENAI_API_CONFIGS='{{"0":{{"enable":true,"model_ids":["anthropic/claude-sonnet-4","google/gemini-2.5-flash","google/gemini-2.5-pro","deepseek/deepseek-chat-v3-0324","anthropic/claude-3.7-sonnet","google/gemini-2.5-flash-lite-preview-06-17","openai/gpt-4.1","x-ai/grok-4","openai/gpt-4o-mini","openai/o4-mini-high","openai/o3","openai/chatgpt-4o-latest"]}}}}'

# ============= DEVELOPMENT FEATURES (ALL ENABLED) =============
ENABLE_TITLE_GENERATION=True
ENABLE_FOLLOW_UP_GENERATION=True
ENABLE_TAGS_GENERATION=True
ENABLE_MESSAGE_RATING=True
ENABLE_COMMUNITY_SHARING=False

ENABLE_IMAGE_GENERATION=True
ENABLE_WEB_SEARCH=True
ENABLE_CODE_EXECUTION=True
ENABLE_CODE_INTERPRETER=True
ENABLE_AUTOCOMPLETE_GENERATION=True

ENABLE_API_KEY=True
ENABLE_API_KEY_ENDPOINT_RESTRICTIONS=False
ENABLE_USER_WEBHOOKS=True

# ============= DATABASE (DEVELOPMENT) =============
DATABASE_URL=sqlite:///${{DATA_DIR}}/webui.db
DATABASE_POOL_SIZE=5
DATABASE_POOL_TIMEOUT=30

# ============= STORAGE =============
DATA_DIR=./data
STATIC_DIR=./static

# ================================================================
# DEVELOPMENT NOTES:
# - Frontend: http://localhost:5173 (Vite with HMR)
# - Backend: http://localhost:8080 (FastAPI with reload)
# - Database: mai_backend_dev_data volume
# - Start: ./dev-hot-reload.sh up
# - Stop: ./dev-hot-reload.sh down
# - Logs: ./dev-hot-reload.sh logs -f
# ================================================================
"""
    
    # Backup existing .env.dev
    if Path('.env.dev').exists():
        backup_name = f'.env.dev.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.rename('.env.dev', backup_name)
        print(f"📋 Backed up existing .env.dev to {backup_name}")
    
    # Write new file
    with open('.env.dev', 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env.dev successfully!")


def main():
    """Main setup process"""
    print("🔧 Simple mAI Development Setup")
    print("=" * 50)
    print()
    
    # Step 1: Get provisioning key
    print("Step 1: OpenRouter Provisioning Key")
    print("Get your key from: https://openrouter.ai/settings/provisioning")
    provisioning_key = input("Enter provisioning key: ").strip()
    
    print("\nValidating key...")
    valid, message = validate_provisioning_key(provisioning_key)
    if not valid:
        print(f"❌ {message}")
        return 1
    print(f"✅ {message}")
    
    # Step 2: Get organization name
    print("\nStep 2: Development Organization")
    org_name = input("Organization name (e.g., 'Dev Testing'): ").strip()
    if not org_name:
        org_name = "Development"
    
    # Step 3: Create API key
    print(f"\nStep 3: Creating API key for '{org_name}'...")
    success, api_key, info = create_api_key(provisioning_key, org_name)
    if not success:
        print(f"❌ Failed to create API key: {info}")
        return 1
    
    print(f"✅ API key created!")
    if info:  # info is key_hash
        print(f"   Key hash: {info}")
    
    # Step 4: Test API key
    print("\nStep 4: Testing API key...")
    success, external_user = test_api_key(api_key, org_name)
    
    if not external_user:
        external_user = generate_external_user(org_name)
        print(f"   Using generated external_user: {external_user}")
    else:
        print(f"✅ Got external_user: {external_user}")
    
    # Step 5: Create .env.dev
    print("\nStep 5: Creating .env.dev file...")
    create_env_dev_file(api_key, org_name, f"dev_{external_user}")
    
    # Step 6: Success message
    print("\n" + "=" * 50)
    print("🎉 Development Setup Complete!")
    print("=" * 50)
    print()
    print(f"📋 Configuration Summary:")
    print(f"   Organization: {org_name} (DEV)")
    print(f"   API Key: {api_key[:20]}...")
    print(f"   External User: dev_{external_user}")
    print()
    print("🚀 Next Steps:")
    print("   1. Start development environment:")
    print("      ./dev-hot-reload.sh up")
    print()
    print("   2. Access application:")
    print("      http://localhost:5173")
    print()
    print("   3. Create admin user:")
    print("      Sign up at the frontend URL")
    print("      First user becomes admin")
    print()
    print("🔥 Hot Reload Ready!")
    print("   Frontend: Changes reflect instantly")
    print("   Backend: Auto-restarts on changes")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)