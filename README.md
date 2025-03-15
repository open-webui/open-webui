# Anthropic Manifold Pipe for Open WebUI

This repository contains custom pipe implementations for Open WebUI to integrate with Anthropic's Claude API.

## Authors
- justinh-rahb (original implementation)
- christian-taillon
- Bermont/Radar (caching implementation and cache control fixes)

## Features

- Supports all Claude models including Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3.5 Haiku, and more
- Implements prompt caching for optimized token usage and cost savings
- Detailed cache usage information displayed in responses
- Image processing with size validation
- Stream mode support

## Installation
Copy and paste into your Open WebUI Function block. Add your Anthropic API and Toggle which Cache functionality you would like or

1. Copy the `anthropic_manifold_pipe.py` file to your Open WebUI pipes directory
2. Set the following environment variables:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `ANTHROPIC_CACHE_TTL` (optional): Cache time-to-live in seconds (default: 3600)
   - `ANTHROPIC_ENABLE_CACHING` (optional): Enable/disable caching (default: true)
   - `ANTHROPIC_SHOW_CACHE_INFO` (optional): Show cache information in responses (default: true)

## Usage

Once installed, the pipe will be available in the Open WebUI interface as a new model provider.

## Caching Implementation

This pipe implements Anthropic's prompt caching feature, which can significantly reduce costs and improve response times by caching frequent prompts. Cache control is implemented using the `{"type": "ephemeral"}` format as required by the Anthropic API.

For more information on prompt caching, see the [Anthropic documentation](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching).

## License

MIT
