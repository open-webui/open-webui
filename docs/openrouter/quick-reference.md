# OpenRouter Models - Quick Reference

## 🚀 Quick Commands

### View Current Models
```bash
docker exec open-webui-staging python /app/manage_models.py list
```

### Add a Model
```bash
docker exec open-webui-staging python /app/manage_models.py add "anthropic/claude-3-opus"
```

### Remove a Model
```bash
docker exec open-webui-staging python /app/manage_models.py remove "openai/o3"
```

### Replace All Models
```bash
docker exec open-webui-staging python /app/manage_models.py set "model1" "model2" "model3"
```

## 📝 Edit Models in File

1. Open `fix_openrouter_docker.py`
2. Edit the `ALLOWED_MODELS` list
3. Run: 
   ```bash
   docker cp fix_openrouter_docker.py open-webui-staging:/app/
   docker exec open-webui-staging python /app/fix_openrouter_docker.py
   ```

## 🔄 After Changes

1. Clear browser cache: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Refresh the page

## 📋 Your Current 12 Models

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

## 🔍 Find New Model IDs

Visit: https://openrouter.ai/models

## ⚡ One-Liner Examples

### Add Claude Opus
```bash
docker exec open-webui-staging python /app/manage_models.py add "anthropic/claude-3-opus"
```

### Remove O3
```bash
docker exec open-webui-staging python /app/manage_models.py remove "openai/o3"
```

### Keep Only Claude Models
```bash
docker exec open-webui-staging python /app/manage_models.py set "anthropic/claude-sonnet-4" "anthropic/claude-3.7-sonnet"
```