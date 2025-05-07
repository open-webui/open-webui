---
sidebar_position: 450
title: "☁️ Azure OpenAI Integration"
---

# Azure OpenAI Integration

Open WebUI supports integration with Azure OpenAI Services, allowing you to connect to your Azure-hosted models alongside other model providers. This guide explains how to set up and use Azure OpenAI with Open WebUI.

## Prerequisites

Before you begin, make sure you have:

- An active Azure subscription
- Access to Azure OpenAI Services
- At least one deployed model in your Azure OpenAI resource
- Your Azure OpenAI endpoint URL and API key

## Adding an Azure OpenAI Connection

To connect Open WebUI to your Azure OpenAI Services:

1. Navigate to **Settings > OpenAI API**
2. Click **Add New Connection**
3. Enter your Azure OpenAI endpoint URL (format: `https://{your-resource-name}.openai.azure.com`)
4. Enter your Azure OpenAI API key
5. Click **Save**

Open WebUI will automatically detect that you're using Azure OpenAI and will fetch your available deployments.

## Model Compatibility

Open WebUI supports different Azure OpenAI model types, each with specific requirements:

### Standard Models (like gpt-4o)

These models use the `2023-03-15-preview` API version by default and work with standard OpenAI parameters.

### O-Series Models (like o4-mini)

These models require:
- API version `2024-12-01-preview`
- Use of `max_completion_tokens` instead of `max_tokens`
- Temperature value of 1 (other values are not supported)

Open WebUI automatically handles these differences, selecting the appropriate API version and converting parameters as needed.

## Environment Variables

You can configure the default Azure OpenAI API version using an environment variable:

```
AZURE_OPENAI_API_VERSION=2023-03-15-preview
```

This is useful when running Open WebUI in Docker or other deployment environments.

## Troubleshooting

### Connection Issues

If you're having trouble connecting to Azure OpenAI:

- Verify your endpoint URL is correct (should be in the format `https://{your-resource-name}.openai.azure.com`)
- Check that your API key is valid and has the necessary permissions
- Ensure your Azure OpenAI resource is in an available state

### Model Not Found

If your models aren't appearing:

- Verify you have deployments created in your Azure OpenAI resource
- Check that your API key has access to the deployments
- Try refreshing the model list in Open WebUI

### API Version Errors

If you see errors related to API versions:

- For o-series models (like o4-mini), ensure they're using API version `2024-12-01-preview`
- For other models, the default `2023-03-15-preview` should work
- You can override the default API version using the environment variable mentioned above

## Limitations

- Azure OpenAI may have different rate limits than standard OpenAI
- Some advanced features might require specific API versions
- Parameter support may vary between different model types

## Additional Resources

- [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure OpenAI API Reference](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)
