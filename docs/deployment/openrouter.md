# OpenRouter Configuration

## Overview

mAI includes OpenRouter model filtering that limits available models to 12 curated choices for all company deployments.

## The 12 Configured Models

1. `anthropic/claude-sonnet-4`
2. `google/gemini-2.5-flash`
3. `google/gemini-2.5-pro`
4. `deepseek/deepseek-chat-v3-0324`
5. `anthropic/claude-3.7-sonnet`
6. `google/gemini-2.5-flash-lite-preview-06-17`
7. `openai/gpt-4.1`
8. `x-ai/grok-4`
9. `openai/gpt-4o-mini`
10. `openai/o4-mini-high`
11. `openai/o3`
12. `openai/chatgpt-4o-latest`

## Quick Setup

### 1. Build Docker Image
```bash
docker build -t mai-production:latest .
```

The OpenRouter scripts are included in the Docker image at `/app/scripts/openrouter/`.

### 2. Initialize Configuration (First Deployment Only)
```bash
# Run once after container starts
docker exec mai-production python /app/scripts/openrouter/production_fix.py init

# Verify configuration
docker exec mai-production python /app/scripts/openrouter/verify_config.py
```

### 3. Access OpenRouter
1. Go to Settings → Connections
2. Add your OpenRouter API key
3. Only the 12 configured models will appear

## Model Management

### List Current Models
```bash
docker exec mai-production python /app/scripts/openrouter/manage_models.py list
```

### Add a Model
```bash
docker exec mai-production python /app/scripts/openrouter/manage_models.py add "model-id"
```

### Remove a Model
```bash
docker exec mai-production python /app/scripts/openrouter/manage_models.py remove "model-id"
```

### Replace All Models
```bash
docker exec mai-production python /app/scripts/openrouter/manage_models.py set "model1" "model2" "model3"
```

## Important Notes

- Configuration persists in the database
- Changes survive container restarts
- No manual script copying needed (scripts in Docker image)
- Same configuration applies to all 20 company deployments
- Clear browser cache after changes: `Ctrl+Shift+R`

## Scripts Reference

Located in `/app/scripts/openrouter/`:
- `production_fix.py` - Initialize/reset configuration
- `manage_models.py` - Add/remove/list models
- `verify_config.py` - Check current configuration