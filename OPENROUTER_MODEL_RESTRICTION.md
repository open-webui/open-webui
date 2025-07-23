# OpenRouter Model Restriction in mAI (Open WebUI)

This document explains how to configure mAI to restrict OpenRouter access to only specific models.

## Overview

Open WebUI already has built-in support for model filtering through the `model_ids` configuration. The system supports both exact model ID matching and wildcard patterns (using `*` and `?`).

## The 12 Allowed Models

Your configuration will limit users to these specific models:

1. **Anthropic: Claude Sonnet 4** - `anthropic/claude-sonnet-4`
2. **Google: Gemini 2.5 Flash** - `google/gemini-2.5-flash`
3. **Google: Gemini 2.5 Pro** - `google/gemini-2.5-pro`
4. **DeepSeek: DeepSeek V3 0324** - `deepseek/deepseek-chat-v3-0324`
5. **Anthropic: Claude 3.7 Sonnet** - `anthropic/claude-3.7-sonnet`
6. **Google: Gemini 2.5 Flash Lite Preview** - `google/gemini-2.5-flash-lite-preview-06-17`
7. **OpenAI: GPT-4.1** - `openai/gpt-4.1`
8. **xAI: Grok 4** - `x-ai/grok-4`
9. **OpenAI: GPT-4o-mini** - `openai/gpt-4o-mini`
10. **OpenAI: o4 Mini High** - `openai/o4-mini-high`
11. **OpenAI: o3** - `openai/o3`
12. **OpenAI: ChatGPT-4o** - `openai/chatgpt-4o-latest`

## Configuration Methods

### Method 1: Via Web UI (Recommended)

1. Log in as an admin user
2. Go to **Settings** > **Admin Panel** > **Connections**
3. Add a new connection with:
   - **Name**: OpenRouter (or any name you prefer)
   - **API Base URL**: `https://openrouter.ai/api/v1`
   - **API Key**: Your OpenRouter API key
4. In the connection settings, look for **Model IDs**
5. Add each of the 12 model IDs listed above

### Method 2: Via API

Use the provided `setup_openrouter_models.py` script:

```bash
python setup_openrouter_models.py
```

The script will guide you through updating the configuration via the API.

### Method 3: Via Environment Variables (Docker)

Add these to your `docker-compose.yml`:

```yaml
services:
  open-webui:
    environment:
      - OPENAI_API_BASE_URLS=["https://openrouter.ai/api/v1"]
      - OPENAI_API_KEYS=["your-openrouter-api-key"]
      - OPENAI_API_CONFIGS='{"0":{"enable":true,"connection_type":"external","model_ids":["anthropic/claude-sonnet-4","google/gemini-2.5-flash","google/gemini-2.5-pro","deepseek/deepseek-chat-v3-0324","anthropic/claude-3.7-sonnet","google/gemini-2.5-flash-lite-preview-06-17","openai/gpt-4.1","x-ai/grok-4","openai/gpt-4o-mini","openai/o4-mini-high","openai/o3","openai/chatgpt-4o-latest"],"tags":["openrouter"]}}'
```

### Method 4: Direct Database Update

If you have direct database access, you can update the `config` table:

```sql
-- Find the openai.api_configs entry
SELECT * FROM config WHERE key = 'openai.api_configs';

-- Update with your configuration
UPDATE config 
SET value = '{"0":{"enable":true,"model_ids":["anthropic/claude-sonnet-4","google/gemini-2.5-flash","google/gemini-2.5-pro","deepseek/deepseek-chat-v3-0324","anthropic/claude-3.7-sonnet","google/gemini-2.5-flash-lite-preview-06-17","openai/gpt-4.1","x-ai/grok-4","openai/gpt-4o-mini","openai/o4-mini-high","openai/o3","openai/chatgpt-4o-latest"]}}'
WHERE key = 'openai.api_configs';
```

## How It Works

1. When a user selects the OpenRouter connection, Open WebUI fetches the available models from OpenRouter's API
2. The system then filters this list based on the `model_ids` configuration
3. Only models that exactly match the IDs in `model_ids` are shown to users
4. The wildcard functionality (`*` and `?`) is also available if you want to use patterns instead

## Wildcard Examples (Alternative Approach)

Instead of listing each model individually, you could use patterns:

```json
{
  "model_ids": [
    "anthropic/claude-*",
    "google/gemini-2.5-*",
    "deepseek/deepseek-chat-v3-*",
    "openai/gpt-4*",
    "openai/o*",
    "openai/chatgpt-*",
    "x-ai/grok-*"
  ]
}
```

However, this might include models you don't want, so exact IDs are recommended for precise control.

## Updating Models

To add or remove models in the future:

1. **Via UI**: Edit the connection and modify the Model IDs list
2. **Via API**: Use the update script with modified `ALLOWED_MODELS`
3. **Via Environment**: Update the `OPENAI_API_CONFIGS` environment variable

## Verification

After configuration, you can verify it's working by:

1. Going to the chat interface
2. Clicking on the model selector dropdown
3. Selecting your OpenRouter connection
4. Confirming only the 12 specified models appear

## Troubleshooting

If all models are still showing:

1. Check that the connection index matches in your configuration
2. Ensure the `model_ids` array is properly formatted
3. Restart the Open WebUI service after configuration changes
4. Clear browser cache and reload

## Security Notes

- Each client should have their own OpenRouter API key
- API keys can be managed through OpenRouter's dashboard
- You can set spending limits per key on OpenRouter
- Monitor usage through OpenRouter's analytics

## Files Included

- `openrouter_models_config.json` - Example configuration
- `setup_openrouter_models.py` - Automated setup script
- `OPENROUTER_MODEL_RESTRICTION.md` - This documentation

## Support

For issues specific to:
- **Model filtering**: Check the Open WebUI logs
- **OpenRouter API**: Refer to https://openrouter.ai/docs
- **mAI customizations**: Follow the guidelines in CLAUDE.md