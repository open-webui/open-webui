# Model Logos Directory - Dynamic Auto-Matching

This directory enables **automatic logo matching** for LLM models.

## ✨ How It Works (Zero-Code Required!)

1. **Drop your logo file here** (e.g., `gpt-5.3.png`)
2. **That's it!** Any model containing "gpt-5.3" in its name will use this logo

The system automatically scans this directory and matches logos based on **filename contains** logic.

## Matching Rules

| Priority | Rule |
|----------|------|
| 1️⃣ | **Longer filenames match first** (more specific) |
| 2️⃣ | **Contains matching** - filename anywhere in model ID |
| 3️⃣ | **Case-insensitive** |

### Examples

| Model ID | Logo File | Match Reason |
|----------|-----------|--------------|
| `gpt-5-mini` | `gpt-5-mini.png` | Exact match |
| `776-gpt-5-mini-abc` | `gpt-5-mini.png` | Contains "gpt-5-mini" |
| `custom/gpt-5.3-turbo` | `gpt-5.3.png` | Contains "gpt-5.3" |
| `my-deepseek-v2` | `deepseek.png` | Contains "deepseek" |
| `gemini-2.0-flash-image-gen` | `nana-banana.png` | Special: gemini + image |
| `BBGDU-v1-chat` | `bbgdu.png` | Contains "bbgdu" (if file exists) |

## Supported Formats

- `.png` (recommended)
- `.svg`
- `.webp`
- `.jpg` / `.jpeg`

## Special Case: Gemini Image Models

If a model ID contains **both** "gemini" **and** "image", it will automatically match `nana-banana.png`.

## Tips

- **Naming**: Use the most distinctive part of the model name
- **Specificity**: If you have both `gpt-5.png` and `gpt-5-mini.png`, the longer one matches first
- **New Models**: Just add the logo file - no code changes needed!
- **Future-proof**: When GPT-6 comes out, just add `gpt-6.png` 🚀

## Cache

Logos are cached for performance. If you add new files, the cache refreshes automatically on next lookup.
For immediate refresh, restart the backend or call `clear_cache()` from the API.
