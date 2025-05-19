# API Key Management

Open WebUI supports managing multiple API keys for providers with various selection strategies. This document explains how to use this feature.

## Overview

The API key management system allows you to:

1. Add multiple API keys for a provider
2. Select a key selection strategy
3. Assign weights to keys for weighted selection

## Key Selection Strategies

The following strategies are available:

### Random (Default)

Selects a random API key for each request. This is useful for distributing load across multiple keys without any specific pattern.

### Round Robin

Cycles through API keys in sequence. This ensures each key is used in turn, providing even distribution of requests across all keys.

### Least Recently Used

Selects the key that was used least recently. This is useful when you want to maximize the time between uses of the same key, which can help with rate limits that reset after a certain period of time.

### Weighted

Selects keys based on their assigned weights. Keys with higher weights will be selected more frequently. This is useful when you have keys with different rate limits or capabilities.

## Adding Multiple API Keys

To add multiple API keys for a provider:

1. Go to the provider's connection settings
2. Toggle the "Multiple Keys" switch to ON
3. Add your API keys using the interface
4. Select a key selection strategy
5. If using the Weighted strategy, assign weights to each key
6. Save your changes

## Implementation Details

### Frontend

The frontend uses the `ApiKeyManager` component to manage multiple API keys and their selection strategy. This component is integrated into the connection modal.

### Backend

The backend uses the `api_key_selection.py` utility to select API keys based on the specified strategy. This utility is used by the API endpoints that need to make requests to external providers.

## Example Usage

### UI Configuration

When adding or editing a connection, you can enable multiple API keys:

1. Toggle "Multiple Keys" to ON
2. Add your API keys
3. Select a strategy
4. If using Weighted strategy, assign weights to each key
5. Save the connection

### Programmatic Usage

The API key selection utility can be used programmatically:

```python
from open_webui.utils.api_key_selection import select_api_key, KeySelectionStrategy

# Example: Select a key using the random strategy (default)
key = select_api_key(
    connection_id="openai-connection-1",
    keys=["sk-key1", "sk-key2", "sk-key3"]
)

# Example: Select a key using the round-robin strategy
key = select_api_key(
    connection_id="openai-connection-1",
    keys=["sk-key1", "sk-key2", "sk-key3"],
    options={
        "strategy": KeySelectionStrategy.ROUND_ROBIN
    }
)

# Example: Select a key using the weighted strategy
key = select_api_key(
    connection_id="openai-connection-1",
    keys=["sk-key1", "sk-key2", "sk-key3"],
    options={
        "strategy": KeySelectionStrategy.WEIGHTED,
        "weights": {
            "sk-key1": 1,  # 1x weight
            "sk-key2": 2,  # 2x weight
            "sk-key3": 3   # 3x weight
        }
    }
)
```

## Benefits

Using multiple API keys with a selection strategy provides several benefits:

1. **Higher throughput**: Distribute requests across multiple keys to increase overall throughput
2. **Rate limit management**: Avoid hitting rate limits by distributing requests across keys
3. **Fallback support**: If one key fails, the system can try another key
4. **Cost distribution**: Distribute costs across multiple accounts or billing entities
5. **Different capabilities**: Use keys with different capabilities or models based on requirements

## Caching

The API key selection system includes caching to improve performance. The cache stores the state of key selection (like which key was used last for round-robin) and can be cleared if needed.

To clear the cache programmatically:

```python
from open_webui.utils.api_key_selection import clear_api_key_cache

# Clear cache for a specific connection
clear_api_key_cache("openai-connection-1")

# Clear all caches
clear_api_key_cache()
```
