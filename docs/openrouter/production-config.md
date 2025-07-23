# Production-Ready OpenRouter Model Management for mAI

## Overview

This solution uses Open WebUI's PersistentConfig system to manage OpenRouter models in production environments without requiring SSH access or manual script execution.

## Initial Setup (One-Time)

### 1. Create Configuration Script

Create `init_openrouter_config.py`:

```python
#!/usr/bin/env python3
"""
Initialize OpenRouter configuration for production deployment.
This script should be run once during initial deployment.
"""

import os
import json

# Default allowed models
DEFAULT_ALLOWED_MODELS = [
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

# Get models from environment variable if provided
env_models = os.environ.get('OPENROUTER_ALLOWED_MODELS', '')
if env_models:
    allowed_models = [m.strip() for m in env_models.split(',') if m.strip()]
else:
    allowed_models = DEFAULT_ALLOWED_MODELS

# Create the configuration
config = {
    "openrouter_config": {
        "enabled": True,
        "allowed_models": allowed_models,
        "model_filter_enabled": True
    }
}

# Output as environment variable format
print(f"OPENROUTER_CONFIG='{json.dumps(config)}'")
```

### 2. Docker Compose Configuration

```yaml
version: '3.8'

services:
  mai:
    image: ghcr.io/open-webui/open-webui:main
    container_name: mai-prod
    environment:
      # Core configuration
      - ENV=prod
      - WEBUI_NAME=mAI
      - WEBUI_URL=https://mai.example.com
      
      # Enable PersistentConfig
      - ENABLE_PERSISTENT_CONFIG=True
      
      # OpenRouter configuration (PersistentConfig)
      - OPENROUTER_ALLOWED_MODELS=anthropic/claude-sonnet-4,google/gemini-2.5-flash,google/gemini-2.5-pro,deepseek/deepseek-chat-v3-0324,anthropic/claude-3.7-sonnet,google/gemini-2.5-flash-lite-preview-06-17,openai/gpt-4.1,x-ai/grok-4,openai/gpt-4o-mini,openai/o4-mini-high,openai/o3,openai/chatgpt-4o-latest
      
      # Database configuration
      - DATABASE_URL=postgresql://user:pass@db:5432/mai
      
    volumes:
      - mai-data:/app/backend/data
      - ./custom_config:/app/custom_config:ro
    ports:
      - "8080:8080"
    networks:
      - mai-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mai
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - mai-network

volumes:
  mai-data:
  postgres-data:

networks:
  mai-network:
```

### 3. Create Admin Management Interface

Create a custom admin tool that can be accessed through Open WebUI:

```python
# /app/custom_config/admin_models.py
"""
Admin interface for managing OpenRouter models.
This can be integrated into Open WebUI's admin panel.
"""

import json
from typing import List, Dict
import sqlite3

class OpenRouterModelManager:
    def __init__(self, db_path: str = '/app/backend/data/webui.db'):
        self.db_path = db_path
    
    def get_current_models(self) -> List[str]:
        """Get current allowed models from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM config WHERE id = 1')
        config_data = json.loads(cursor.fetchone()[0])
        
        conn.close()
        
        # Navigate to OpenRouter config
        openai_config = config_data.get('openai', {})
        api_configs = openai_config.get('api_configs', {})
        
        # Find OpenRouter configuration
        for idx, url in enumerate(openai_config.get('api_base_urls', [])):
            if 'openrouter.ai' in url:
                return api_configs.get(str(idx), {}).get('model_ids', [])
        
        return []
    
    def update_models(self, models: List[str]) -> bool:
        """Update allowed models in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current config
        cursor.execute('SELECT id, data FROM config WHERE id = 1')
        config_id, config_data = cursor.fetchone()
        config = json.loads(config_data)
        
        # Find and update OpenRouter config
        openai_config = config.get('openai', {})
        api_urls = openai_config.get('api_base_urls', [])
        
        for idx, url in enumerate(api_urls):
            if 'openrouter.ai' in url:
                if 'api_configs' not in openai_config:
                    openai_config['api_configs'] = {}
                
                openai_config['api_configs'][str(idx)] = {
                    'enable': True,
                    'connection_type': 'external',
                    'model_ids': models,
                    'tags': ['openrouter', 'production']
                }
                break
        
        # Save updated config
        cursor.execute(
            'UPDATE config SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(config), config_id)
        )
        
        conn.commit()
        conn.close()
        
        return True

# Example API endpoints that could be added to Open WebUI
def api_get_models():
    """API endpoint to get current models."""
    manager = OpenRouterModelManager()
    return {"models": manager.get_current_models()}

def api_update_models(models: List[str]):
    """API endpoint to update models."""
    manager = OpenRouterModelManager()
    success = manager.update_models(models)
    return {"success": success, "models": models}
```

## Production Deployment Options

### Option 1: Environment Variable Configuration

For Hetzner or other cloud deployments, use environment variables in your deployment configuration:

```bash
# .env.production
OPENROUTER_ALLOWED_MODELS="anthropic/claude-sonnet-4,google/gemini-2.5-flash,google/gemini-2.5-pro"
```

### Option 2: Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mai-config
data:
  OPENROUTER_ALLOWED_MODELS: |
    anthropic/claude-sonnet-4,
    google/gemini-2.5-flash,
    google/gemini-2.5-pro,
    deepseek/deepseek-chat-v3-0324,
    anthropic/claude-3.7-sonnet,
    google/gemini-2.5-flash-lite-preview-06-17,
    openai/gpt-4.1,
    x-ai/grok-4,
    openai/gpt-4o-mini,
    openai/o4-mini-high,
    openai/o3,
    openai/chatgpt-4o-latest
```

### Option 3: Ansible Playbook

```yaml
---
- name: Deploy mAI with OpenRouter Configuration
  hosts: mai_servers
  vars:
    openrouter_models:
      - anthropic/claude-sonnet-4
      - google/gemini-2.5-flash
      - google/gemini-2.5-pro
      # ... other models
  
  tasks:
    - name: Create docker-compose file
      template:
        src: docker-compose.yml.j2
        dest: /opt/mai/docker-compose.yml
      vars:
        models_list: "{{ openrouter_models | join(',') }}"
    
    - name: Deploy mAI
      docker_compose:
        project_src: /opt/mai
        state: present
```

## Web-Based Management Interface

Create a simple web interface for model management:

```html
<!DOCTYPE html>
<html>
<head>
    <title>mAI OpenRouter Model Manager</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .model-list { margin: 20px 0; }
        .model-item { padding: 10px; margin: 5px 0; background: #f0f0f0; }
        button { padding: 10px 20px; margin: 10px 0; }
        .add-model { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>OpenRouter Model Management</h1>
    
    <div id="models-container">
        <h2>Current Models</h2>
        <div id="model-list" class="model-list"></div>
    </div>
    
    <div class="add-model">
        <h3>Add New Model</h3>
        <input type="text" id="new-model" placeholder="e.g., anthropic/claude-3-opus">
        <button onclick="addModel()">Add Model</button>
    </div>
    
    <button onclick="saveChanges()">Save Changes</button>
    
    <script>
        let currentModels = [];
        
        async function loadModels() {
            const response = await fetch('/api/admin/openrouter/models');
            const data = await response.json();
            currentModels = data.models;
            displayModels();
        }
        
        function displayModels() {
            const container = document.getElementById('model-list');
            container.innerHTML = currentModels.map((model, idx) => `
                <div class="model-item">
                    ${model}
                    <button onclick="removeModel(${idx})">Remove</button>
                </div>
            `).join('');
        }
        
        function addModel() {
            const input = document.getElementById('new-model');
            if (input.value && !currentModels.includes(input.value)) {
                currentModels.push(input.value);
                displayModels();
                input.value = '';
            }
        }
        
        function removeModel(idx) {
            currentModels.splice(idx, 1);
            displayModels();
        }
        
        async function saveChanges() {
            const response = await fetch('/api/admin/openrouter/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ models: currentModels })
            });
            
            if (response.ok) {
                alert('Models updated successfully!');
            }
        }
        
        // Load models on page load
        loadModels();
    </script>
</body>
</html>
```

## Advantages of This Approach

1. **No SSH Required**: After initial deployment, all changes can be made through web interface
2. **Multi-Client Support**: Each deployment can have different model lists via environment variables
3. **Persistent Configuration**: Settings survive container restarts
4. **Easy Updates**: Models can be updated through:
   - Admin web interface
   - Environment variable changes (requires restart)
   - API calls
5. **Audit Trail**: Database changes are timestamped
6. **Scalable**: Works with Docker, Kubernetes, or any container orchestration

## Quick Reference Commands

### Initial Deployment
```bash
# Deploy with specific models
docker run -d \
  --name mai-client1 \
  -e OPENROUTER_ALLOWED_MODELS="model1,model2,model3" \
  -e WEBUI_NAME="Client 1 mAI" \
  ghcr.io/open-webui/open-webui:main
```

### Update Models (After Deployment)
1. Access Admin Panel: `https://mai.example.com/admin`
2. Navigate to Settings → Connections → OpenRouter
3. Update model list
4. Save changes (no restart required)

### Verify Configuration
```bash
# Check current models via API
curl -H "Authorization: Bearer $API_KEY" \
  https://mai.example.com/api/admin/openrouter/models
```

## Security Considerations

1. **API Authentication**: Ensure admin endpoints require authentication
2. **HTTPS Only**: Always use HTTPS in production
3. **Environment Variables**: Use secrets management for sensitive data
4. **Access Control**: Limit admin access to authorized personnel only

This solution provides a production-ready, scalable approach to managing OpenRouter models across multiple mAI deployments without requiring direct server access.