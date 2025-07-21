# mAI Customization Extraction Plan

## Overview
This document outlines the plan to refactor mAI customizations from hardcoded changes to a configuration-based system, making updates and client deployments significantly easier.

## Goals
1. **Zero-conflict updates**: Merge Open WebUI updates without any conflicts
2. **Client flexibility**: Easy per-client customization without code changes
3. **Maintainability**: Single source of truth for all customizations
4. **Backward compatibility**: Preserve all existing functionality

## Phase 1: Configuration System Design

### 1.1 Configuration Structure
```
config/
├── default/
│   ├── branding.json      # Default mAI branding
│   ├── themes.json        # Custom theme definitions
│   ├── features.json      # Feature toggles
│   └── locales.json       # Additional translations
├── clients/
│   ├── client-a/
│   │   └── config.json    # Client-specific overrides
│   └── client-b/
│       └── config.json
└── schema/
    └── config.schema.json # JSON schema for validation
```

### 1.2 Configuration Schema
```json
{
  "branding": {
    "appName": "mAI",
    "tagline": {
      "en": "You + AI = superpowers! 🚀",
      "pl": "Ty + AI = supermoce! 🚀"
    },
    "logo": {
      "light": "/custom/assets/logo.png",
      "dark": "/custom/assets/logo-dark.png"
    },
    "favicon": "/custom/assets/favicon.png",
    "pwa": {
      "name": "mAI",
      "shortName": "mAI",
      "description": "You + AI = superpowers!"
    }
  },
  "features": {
    "backgroundPatterns": {
      "enabled": true,
      "types": ["dots", "grid", "diagonal"],
      "defaultOpacity": 0.1
    },
    "customThemes": {
      "enabled": true,
      "themes": ["professional", "minimalist", "creative", "warm"]
    },
    "fontSizeControl": {
      "enabled": true,
      "sizes": ["small", "normal", "large", "xlarge"]
    }
  },
  "themes": {
    "professional": {
      "name": "mAI Professional",
      "icon": "🔧",
      "colors": {
        "primary": "#8B4513",
        "secondary": "#D2691E"
      }
    }
  }
}
```

## Phase 2: Implementation Steps

### 2.1 Backend Configuration Loader
```python
# backend/open_webui/config_loader.py
import json
import os
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, client_id: str = None):
        self.client_id = client_id
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        # Load default config
        default_config = self._load_json("config/default")
        
        # Override with client config if specified
        if self.client_id:
            client_config = self._load_json(f"config/clients/{self.client_id}")
            return self._deep_merge(default_config, client_config)
        
        return default_config
```

### 2.2 Frontend Configuration Injection
```typescript
// src/lib/config/index.ts
export interface AppConfig {
  branding: BrandingConfig;
  features: FeaturesConfig;
  themes: ThemesConfig;
}

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch('/api/config');
  return response.json();
}

// Use in components
import { loadConfig } from '$lib/config';

const config = await loadConfig();
const appName = config.branding.appName; // "mAI"
```

### 2.3 Build-Time Configuration
```javascript
// vite.config.ts
import { loadConfig } from './scripts/config-loader';

export default defineConfig(async () => {
  const config = await loadConfig(process.env.CLIENT_ID);
  
  return {
    define: {
      __APP_CONFIG__: JSON.stringify(config)
    }
  };
});
```

## Phase 3: Migration Plan

### 3.1 Extract Current Hardcoded Values
1. **Branding Constants**
   - `APP_NAME = "mAI"` → `config.branding.appName`
   - `APP_TAGLINE` → `config.branding.tagline`

2. **Asset Paths**
   - Static favicon references → Dynamic config paths
   - Logo imports → Config-based URLs

3. **Feature Flags**
   - Background patterns code → Feature toggle
   - Theme definitions → Config-driven

### 3.2 Create Compatibility Layer
```typescript
// src/lib/compat/constants.ts
import { config } from '$lib/config';

// Maintain backward compatibility
export const APP_NAME = config.branding.appName;
export const APP_TAGLINE = config.branding.tagline[currentLocale];
```

### 3.3 Update Components Gradually
1. Start with non-critical components
2. Test each change thoroughly
3. Update critical components last
4. Maintain fallbacks during transition

## Phase 4: Client Deployment System

### 4.1 Client Configuration Template
```yaml
# config/clients/template/config.yaml
client:
  id: "client-id"
  name: "Client Name"
  domain: "ai.client.com"

branding:
  appName: "Client AI"
  tagline:
    en: "Powered by mAI"
  
features:
  backgroundPatterns:
    enabled: false
  customThemes:
    enabled: true
    themes: ["professional"]

deployment:
  environment: "production"
  auth:
    type: "oidc"
    provider: "keycloak"
```

### 4.2 Deployment Script
```bash
#!/bin/bash
# deploy-client.sh

CLIENT_ID=$1
ENVIRONMENT=$2

# Load client config
CONFIG_PATH="config/clients/${CLIENT_ID}/config.yaml"

# Build with client config
docker build \
  --build-arg CLIENT_ID=${CLIENT_ID} \
  --build-arg CONFIG_PATH=${CONFIG_PATH} \
  -t mai-${CLIENT_ID}:latest .

# Deploy to environment
docker tag mai-${CLIENT_ID}:latest registry.hetzner.com/mai-${CLIENT_ID}:latest
docker push registry.hetzner.com/mai-${CLIENT_ID}:latest
```

## Phase 5: Testing Strategy

### 5.1 Configuration Validation
```javascript
// tests/config.test.js
describe('Configuration System', () => {
  test('Default config loads correctly', async () => {
    const config = await loadConfig();
    expect(config.branding.appName).toBe('mAI');
  });
  
  test('Client override works', async () => {
    const config = await loadConfig('client-a');
    expect(config.branding.appName).toBe('Client A Portal');
  });
});
```

### 5.2 Migration Testing
1. **Before**: Screenshot all UI elements
2. **After**: Verify identical appearance
3. **Performance**: Ensure no degradation
4. **Builds**: Test production builds
