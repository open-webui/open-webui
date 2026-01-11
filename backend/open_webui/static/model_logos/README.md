# Model Logos Directory

This directory contains brand logos for automatic model icon matching.

## How It Works

When a model is added (e.g., `gpt-4o-mini`), the system automatically matches it to a brand logo based on keywords in the model ID.

**NEW**: GPT models now have individual logo matching (gpt-4o, gpt-5, o1, o3, etc.)

## Supported File Formats

- `.png` (recommended)
- `.svg`
- `.webp`
- `.jpg` / `.jpeg`

## Adding New Logos

1. Add your logo file to this directory
2. Name it after the brand (e.g., `gpt-4o.png`, `anthropic.svg`)
3. The matching keywords are defined in `utils/model_logos.py`

## OpenAI / GPT Models (Individual Logos)

| Filename | Matches |
|----------|---------|
| `gpt-5.png` | gpt-5, gpt-5-xxx |
| `gpt-5-codex.png` | gpt-5-codex |
| `gpt-5-chat-latest.png` | gpt-5-chat-latest |
| `gpt-5-mini.png` | gpt-5-mini |
| `gpt-5-nano.png` | gpt-5-nano |
| `gpt-5.1.png` | gpt-5.1 |
| `gpt-5.2.png` | gpt-5.2 |
| `gpt-4.1.png` | gpt-4.1, gpt-4.1-xxx |
| `gpt-4.1-mini.png` | gpt-4.1-mini |
| `gpt-4.1-nano.png` | gpt-4.1-nano |
| `gpt-4o.png` | gpt-4o, gpt-4o-xxx |
| `gpt-4o-mini.png` | gpt-4o-mini |
| `gpt-4.png` | gpt-4, gpt-4-turbo |
| `gpt-3.5.png` | gpt-3.5-turbo |
| `gpt-oss-20b.png` | gpt-oss-20b |
| `o3.png` | o3, o3-xxx |
| `o3-mini.png` | o3-mini |
| `o1.png` | o1, o1-xxx |
| `o1-mini.png` | o1-mini |
| `openai.png` | Only when model contains "openai" |

## Google / Gemini Models

| Filename | Matches |
|----------|---------|
| `nana-banana.png` | **gemini + image** (e.g., gemini-2.0-flash-image-generation) |
| `google.png` | gemini, google, palm, bard |
| `gemma.png` | gemma |

## Other Brands

| Filename | Matches |
|----------|---------|
| `anthropic.png` | claude, anthropic |
| `meta.png` | llama, meta |
| `mistral.png` | mistral, mixtral |
| `deepseek.png` | deepseek |
| `qwen.png` | qwen, tongyi, alibaba |
| `zhipu.png` | glm, chatglm, zhipu |
| `doubao.png` | doubao, bytedance |
| `kimi.png` | kimi, moonshot |
| `minimax.png` | minimax, abab |
| `xai.png` | grok, xai |
| `yi.png` | yi- |
| `baichuan.png` | baichuan |
| `cohere.png` | cohere, command |
| `microsoft.png` | phi-, bing, microsoft |
| `huggingface.png` | huggingface |
| `perplexity.png` | perplexity, pplx |
| `groq.png` | groq |
| `together.png` | together |
| `fireworks.png` | fireworks |
| `stability.png` | stable-diffusion, sdxl |
| `amazon.png` | titan, bedrock |
| `ollama.png` | ollama |

## Note

Logo files are NOT included in this repository due to trademark concerns.
Please download official logos from each provider's brand resources page.
