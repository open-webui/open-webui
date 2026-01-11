# Model Logos Directory

This directory contains brand logos for automatic model icon matching.

## How It Works

When a model is added (e.g., `gpt-4o-mini`), the system automatically matches it to a brand logo based on keywords in the model ID.

## Supported File Formats

- `.png` (recommended)
- `.svg`
- `.webp`
- `.jpg` / `.jpeg`

## Adding New Logos

1. Add your logo file to this directory
2. Name it after the brand (e.g., `openai.png`, `anthropic.svg`)
3. The matching keywords are defined in `utils/model_logos.py`

## Supported Brands

| Filename | Matches |
|----------|---------|
| `openai.png` | gpt-4, o1-, chatgpt, etc. |
| `anthropic.png` | claude-3, claude-2, etc. |
| `google.png` | gemini, gemma, palm |
| `meta.png` | llama, codellama |
| `mistral.png` | mistral, mixtral |
| `deepseek.png` | deepseek |
| `qwen.png` | qwen, tongyi |
| `zhipu.png` | glm, chatglm |
| `doubao.png` | doubao |
| `kimi.png` | kimi, moonshot |
| `minimax.png` | minimax, abab |
| `xai.png` | grok |
| `yi.png` | yi- |
| `baichuan.png` | baichuan |
| `ollama.png` | ollama |
| `groq.png` | groq |
| `cohere.png` | cohere, command |
| `microsoft.png` | phi-, bing |
| `huggingface.png` | huggingface |
| `perplexity.png` | perplexity, pplx |
| `together.png` | together |
| `fireworks.png` | fireworks |
| `stability.png` | stable-diffusion, sdxl |
| `amazon.png` | titan, bedrock |

## Note

Logo files are NOT included in this repository due to trademark concerns.
Please download official logos from each provider's brand resources page.
