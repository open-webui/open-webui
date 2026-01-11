"""
Model Logo Auto-Loading Utility

This module provides automatic logo matching for LLM models based on their
model ID or name. It maps model identifiers to brand logos stored in the
static/model_logos directory.

This is a custom enhancement that minimizes merge conflicts with upstream
by isolating all logic in this new file.
"""

import os
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Directory where brand logos are stored
LOGOS_DIR = Path(__file__).parent.parent / "static" / "model_logos"

# Brand keyword mappings: keywords -> logo filename (without extension)
# The first matching keyword wins, so order matters for ambiguous cases
BRAND_KEYWORDS = {
    # OpenAI
    "openai": "openai",
    "gpt-": "openai",
    "gpt4": "openai",
    "o1-": "openai",
    "o3-": "openai",
    "chatgpt": "openai",
    "text-davinci": "openai",
    "text-embedding": "openai",
    "dall-e": "openai",
    "whisper": "openai",
    "tts-": "openai",
    
    # Anthropic Claude
    "anthropic": "anthropic",
    "claude": "anthropic",
    
    # Google
    "google": "google",
    "gemini": "google",
    "gemma": "google",
    "palm": "google",
    "bard": "google",
    
    # Meta Llama
    "meta": "meta",
    "llama": "meta",
    "codellama": "meta",
    
    # Mistral
    "mistral": "mistral",
    "mixtral": "mistral",
    "codestral": "mistral",
    "pixtral": "mistral",
    
    # DeepSeek
    "deepseek": "deepseek",
    
    # Alibaba Qwen
    "qwen": "qwen",
    "tongyi": "qwen",
    "alibaba": "qwen",
    
    # Zhipu AI (GLM)
    "zhipu": "zhipu",
    "glm": "zhipu",
    "chatglm": "zhipu",
    
    # ByteDance Doubao
    "doubao": "doubao",
    "bytedance": "doubao",
    
    # Moonshot Kimi
    "kimi": "kimi",
    "moonshot": "kimi",
    
    # Minimax
    "minimax": "minimax",
    "abab": "minimax",
    
    # xAI Grok
    "grok": "xai",
    "xai": "xai",
    
    # Cohere
    "cohere": "cohere",
    "command": "cohere",
    
    # 01.AI Yi
    "01.ai": "yi",
    "yi-": "yi",
    
    # Baichuan
    "baichuan": "baichuan",
    
    # Hugging Face
    "huggingface": "huggingface",
    "hf.co": "huggingface",
    
    # Microsoft
    "microsoft": "microsoft",
    "phi-": "microsoft",
    "bing": "microsoft",
    
    # Amazon
    "amazon": "amazon",
    "titan": "amazon",
    "bedrock": "amazon",
    
    # Stability AI
    "stability": "stability",
    "stable-diffusion": "stability",
    "sdxl": "stability",
    
    # Ollama (local)
    "ollama": "ollama",
    
    # Perplexity
    "perplexity": "perplexity",
    "pplx": "perplexity",
    
    # Together AI
    "together": "together",
    
    # Groq
    "groq": "groq",
    
    # Fireworks
    "fireworks": "fireworks",
    
    # Replicate
    "replicate": "replicate",
    
    # Inflection
    "inflection": "inflection",
    "pi": "inflection",
}

# Supported image extensions (in priority order)
SUPPORTED_EXTENSIONS = [".png", ".svg", ".webp", ".jpg", ".jpeg"]

# Cache for resolved logo paths (performance optimization)
_logo_cache: dict[str, Optional[str]] = {}


def get_brand_for_model(model_id: str) -> Optional[str]:
    """
    Determine the brand name for a given model ID.
    
    Args:
        model_id: The model identifier (e.g., "gpt-4o-mini", "claude-3-opus")
    
    Returns:
        Brand name (logo filename without extension) or None if no match
    """
    model_id_lower = model_id.lower()
    
    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword in model_id_lower:
            return brand
    
    return None


def get_logo_path(model_id: str) -> Optional[Path]:
    """
    Get the filesystem path to the logo for a given model ID.
    
    Args:
        model_id: The model identifier
    
    Returns:
        Path to the logo file, or None if no matching logo exists
    """
    # Check cache first
    if model_id in _logo_cache:
        cached = _logo_cache[model_id]
        return Path(cached) if cached else None
    
    brand = get_brand_for_model(model_id)
    if not brand:
        _logo_cache[model_id] = None
        return None
    
    # Look for logo file with supported extensions
    for ext in SUPPORTED_EXTENSIONS:
        logo_path = LOGOS_DIR / f"{brand}{ext}"
        if logo_path.exists():
            _logo_cache[model_id] = str(logo_path)
            log.debug(f"Logo matched for model '{model_id}': {logo_path}")
            return logo_path
    
    _logo_cache[model_id] = None
    return None


def get_logo_bytes(model_id: str) -> Optional[tuple[bytes, str]]:
    """
    Read and return the logo bytes for a given model ID.
    
    Args:
        model_id: The model identifier
    
    Returns:
        Tuple of (bytes, content_type) or None if no logo found
    """
    logo_path = get_logo_path(model_id)
    if not logo_path:
        return None
    
    try:
        content = logo_path.read_bytes()
        
        # Determine content type
        ext = logo_path.suffix.lower()
        content_types = {
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        content_type = content_types.get(ext, "image/png")
        
        return (content, content_type)
    except Exception as e:
        log.error(f"Failed to read logo file {logo_path}: {e}")
        return None


def clear_cache():
    """Clear the logo path cache. Useful after adding new logo files."""
    global _logo_cache
    _logo_cache = {}


def list_available_brands() -> list[str]:
    """List all brands that have logo files available."""
    brands = set()
    if LOGOS_DIR.exists():
        for ext in SUPPORTED_EXTENSIONS:
            for logo_file in LOGOS_DIR.glob(f"*{ext}"):
                brands.add(logo_file.stem)
    return sorted(brands)
