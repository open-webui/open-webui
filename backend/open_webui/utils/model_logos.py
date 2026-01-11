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

# =============================================================================
# Brand keyword mappings: keywords -> logo filename (without extension)
# ORDER MATTERS! More specific patterns should come BEFORE generic ones.
# =============================================================================

# Ordered list of (keyword, logo_name) tuples for precise matching
# Use tuples instead of dict to maintain order in older Python versions
BRAND_KEYWORDS_ORDERED = [
    # =========================================================================
    # OpenAI GPT Models - Individual logos (MOST SPECIFIC FIRST)
    # Matching uses "contains" logic, so "abc-gpt-5-mini-xyz" will match "gpt-5-mini"
    # =========================================================================
    # GPT-5 series (most specific first)
    ("gpt-5-codex", "gpt-5-codex"),
    ("gpt-5-chat-latest", "gpt-5-chat-latest"),
    ("gpt-5-mini", "gpt-5-mini"),
    ("gpt-5-nano", "gpt-5-nano"),
    ("gpt-5.2-pro", "gpt-5.2-pro"),
    ("gpt-5.2", "gpt-5.2"),
    ("gpt-5.1", "gpt-5.1"),
    ("gpt-5-pro", "gpt-5-pro"),
    ("gpt-5", "gpt-5"),
    
    # GPT-4.1 series
    ("gpt-4.1-mini", "gpt-4.1-mini"),
    ("gpt-4.1-nano", "gpt-4.1-nano"),
    ("gpt-4.1", "gpt-4.1"),
    
    # GPT-4o series
    ("gpt-4o-mini", "gpt-4o-mini"),
    ("gpt-4o", "gpt-4o"),
    
    # GPT-4 Turbo and base
    ("gpt-4-turbo", "gpt-4-turbo"),
    ("gpt-4", "gpt-4"),
    
    # GPT-3.5
    ("gpt-3.5", "gpt-3.5"),
    
    # GPT-OSS special models (larger models first)
    ("gpt-oss-120b", "gpt-oss-120b"),
    ("gpt-oss-20b", "gpt-oss-20b"),
    
    # O-series models (OpenAI reasoning models)
    ("o3-mini", "o3-mini"),
    ("o3", "o3"),
    ("o1-mini", "o1-mini"),
    ("o1-preview", "o1-preview"),
    ("o1", "o1"),
    
    # OpenAI other services
    ("chatgpt", "chatgpt"),
    ("text-davinci", "openai"),
    ("text-embedding", "openai"),
    ("dall-e", "dall-e"),
    ("whisper", "whisper"),
    ("tts-", "openai"),
    
    # OpenAI fallback - ONLY when explicitly contains "openai"
    ("openai", "openai"),
    
    # =========================================================================
    # Google / Gemini Models
    # =========================================================================
    # Nana Banana - Gemini image generation models (handled specially below)
    # Note: "gemini" + "image" combination is handled in get_brand_for_model()
    
    ("gemma", "gemma"),
    ("gemini", "google"),
    ("google", "google"),
    ("palm", "google"),
    ("bard", "google"),
    
    # =========================================================================
    # Anthropic Claude
    # =========================================================================
    ("claude", "anthropic"),
    ("anthropic", "anthropic"),
    
    # =========================================================================
    # Meta Llama
    # =========================================================================
    ("codellama", "codellama"),
    ("llama", "meta"),
    ("meta", "meta"),
    
    # =========================================================================
    # Mistral
    # =========================================================================
    ("codestral", "codestral"),
    ("pixtral", "pixtral"),
    ("mixtral", "mixtral"),
    ("mistral", "mistral"),
    
    # =========================================================================
    # DeepSeek
    # =========================================================================
    ("deepseek", "deepseek"),
    
    # =========================================================================
    # Chinese LLM Providers
    # =========================================================================
    # Alibaba Qwen
    ("qwen", "qwen"),
    ("tongyi", "qwen"),
    ("alibaba", "qwen"),
    
    # Zhipu AI (GLM)
    ("chatglm", "zhipu"),
    ("glm-", "zhipu"),
    ("glm4", "zhipu"),
    ("zhipu", "zhipu"),
    
    # ByteDance Doubao
    ("doubao", "doubao"),
    ("bytedance", "doubao"),
    
    # Moonshot Kimi
    ("kimi", "kimi"),
    ("moonshot", "kimi"),
    
    # Minimax
    ("minimax", "minimax"),
    ("abab", "minimax"),
    
    # 01.AI Yi
    ("yi-", "yi"),
    ("01.ai", "yi"),
    
    # Baichuan
    ("baichuan", "baichuan"),
    
    # =========================================================================
    # Other Providers
    # =========================================================================
    # xAI Grok
    ("grok", "xai"),
    ("xai", "xai"),
    
    # Cohere
    ("command-r", "cohere"),
    ("command", "cohere"),
    ("cohere", "cohere"),
    
    # Microsoft
    ("phi-", "microsoft"),
    ("bing", "microsoft"),
    ("microsoft", "microsoft"),
    
    # Amazon
    ("titan", "amazon"),
    ("bedrock", "amazon"),
    ("amazon", "amazon"),
    
    # Stability AI
    ("stable-diffusion", "stability"),
    ("sdxl", "stability"),
    ("stability", "stability"),
    
    # Hugging Face
    ("huggingface", "huggingface"),
    ("hf.co", "huggingface"),
    
    # Perplexity
    ("pplx", "perplexity"),
    ("perplexity", "perplexity"),
    
    # Infrastructure providers
    ("groq", "groq"),
    ("together", "together"),
    ("fireworks", "fireworks"),
    ("replicate", "replicate"),
    ("ollama", "ollama"),
    
    # Inflection
    ("inflection", "inflection"),
]

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
    
    # Special case: Gemini image models -> nana-banana
    if "gemini" in model_id_lower and "image" in model_id_lower:
        return "nana-banana"
    
    # Iterate through ordered keywords (specific patterns first)
    for keyword, brand in BRAND_KEYWORDS_ORDERED:
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
