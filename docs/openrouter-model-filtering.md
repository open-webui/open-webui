# OpenRouter Model Filtering with Wildcards

## Overview

Open WebUI now supports wildcard pattern matching for filtering models from OpenRouter and other OpenAI-compatible APIs. This feature allows you to show only specific models based on patterns, making it easier to manage large model lists.

## Configuration

When adding an OpenRouter connection in Open WebUI:

1. Go to **Settings** → **Connections** → **Add Connection**
2. Enter your OpenRouter URL and API key
3. In the **Model IDs** section, you can now use wildcard patterns

## Wildcard Pattern Syntax

The feature uses glob-style pattern matching:
- `*` matches any sequence of characters
- `?` matches any single character

## Examples

### Show only OpenAI models
```
openai/*
```

### Show only Anthropic Claude models
```
anthropic/*
```

### Show specific Claude 3 models
```
anthropic/claude-3*
```

### Show all 32k context models
```
*-32k
```

### Combine multiple patterns
You can add multiple patterns to show models from different providers:
```
openai/*
anthropic/claude-3*
meta-llama/*
```

### Show models with specific characteristics
```
*-instruct     # All instruction-tuned models
*turbo*        # All models with "turbo" in the name
gpt-4*         # All GPT-4 variants
```

## Backward Compatibility

If you don't use wildcards (no `*` or `?` in model IDs), the system will use exact matching as before. This ensures existing configurations continue to work without changes.

## How It Works

1. When wildcard patterns are detected in `model_ids`, the system fetches the full model list from the API
2. Each model is checked against all patterns using fnmatch pattern matching
3. Only models matching at least one pattern are shown in the UI

## Benefits

- **Simplified Management**: No need to manually add each model ID
- **Dynamic Updates**: Automatically includes new models that match your patterns
- **Provider Filtering**: Easily show models from specific providers
- **Flexible Selection**: Use patterns to select models by various criteria

## Troubleshooting

If models aren't appearing as expected:
1. Verify your patterns are correct (case-sensitive)
2. Check that the connection is enabled
3. Ensure your API key has access to the models
4. Try refreshing the model list in the UI