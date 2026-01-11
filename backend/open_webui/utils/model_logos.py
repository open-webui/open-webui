"""
Model Logo Auto-Loading Utility

This module provides DYNAMIC automatic logo matching for LLM models.
It scans the static/model_logos directory and matches logo filenames
against model IDs using smart fuzzy matching.

HOW IT WORKS:
1. Scans all logo files in static/model_logos/ directory
2. Extracts keywords from filenames (removing suffixes like -color, -icon)
3. Uses multiple matching strategies for maximum flexibility
4. No need to rename files perfectly - just drop them in!

This is a custom enhancement that minimizes merge conflicts with upstream
by isolating all logic in this new file.
"""

import re
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Directory where brand logos are stored
LOGOS_DIR = Path(__file__).parent.parent / "static" / "model_logos"

# Supported image extensions (in priority order)
SUPPORTED_EXTENSIONS = [".png", ".svg", ".webp", ".jpg", ".jpeg"]

# =============================================================================
# Caches for performance optimization
# =============================================================================
_logo_cache: dict[str, Optional[str]] = {}
_available_logos_cache: Optional[list[tuple[list[str], Path]]] = None


def _normalize_name(name: str) -> str:
    """
    Normalize a name by removing common suffixes and cleaning up.
    """
    name = name.lower().strip()
    name = name.replace(" ", "-")
    
    # Remove common suffixes like -color, -icon, -logo (can appear anywhere)
    name = re.sub(r'[-_]?(color|icon|logo|brand|official)', '', name)
    
    # Remove version numbers like (1), (2), _v2, -v1
    name = re.sub(r'[-_\s]?\(\d+\)', '', name)
    name = re.sub(r'[-_]?v\d+$', '', name)
    
    # Remove trailing/leading hyphens/underscores
    name = name.strip('-_')
    
    return name


def _extract_all_keywords(name: str) -> list[str]:
    """
    Extract ALL possible keywords from a filename for maximum matching flexibility.
    
    Examples:
        "Google-gemini-icon" -> ["google-gemini", "google", "gemini", "googlegemini"]
        "deepseek-color (1)" -> ["deepseek", "deepseekcolor"]
        "qwen-color (1)" -> ["qwen", "qwencolor"]
        "nana banana" -> ["nana-banana", "nana", "banana", "nanabanana"]
    """
    keywords = set()
    
    original = name.lower().strip()
    
    # Normalized version (removes -color, -icon, etc.)
    normalized = _normalize_name(original)
    if normalized and len(normalized) >= 2:
        keywords.add(normalized)
    
    # Version without any delimiters
    no_delimiters = re.sub(r'[-_\s\(\)\d]+', '', original)
    if no_delimiters and len(no_delimiters) >= 2:
        keywords.add(no_delimiters)
    
    # Split by delimiters and add each meaningful part
    parts = re.split(r'[-_\s\(\)]+', original)
    for part in parts:
        # Skip common suffixes and very short parts
        if part and len(part) >= 2 and part not in ('color', 'icon', 'logo', 'brand', 'official', 'svg', 'png', 'jpg'):
            # Skip numeric-only parts
            if not part.isdigit():
                keywords.add(part)
    
    # Also add normalized parts
    normalized_parts = re.split(r'[-_\s]+', normalized)
    for part in normalized_parts:
        if part and len(part) >= 2:
            keywords.add(part)
    
    # Special handling: remove leading/trailing numbers from keywords
    cleaned_keywords = set()
    for kw in keywords:
        cleaned = re.sub(r'^\d+|\d+$', '', kw).strip('-_')
        if cleaned and len(cleaned) >= 2:
            cleaned_keywords.add(cleaned)
    
    return list(cleaned_keywords | keywords)


def _scan_available_logos() -> list[tuple[list[str], Path]]:
    """
    Scan the logos directory and return all available logo files with their keywords.
    
    Returns:
        List of (keywords_list, logo_path) tuples,
        sorted by longest keyword length (for more specific matching).
    """
    global _available_logos_cache
    
    if _available_logos_cache is not None:
        return _available_logos_cache
    
    logos = []
    if LOGOS_DIR.exists():
        for ext in SUPPORTED_EXTENSIONS:
            for logo_file in LOGOS_DIR.glob(f"*{ext}"):
                filename = logo_file.stem
                # Skip README and other non-logo files
                if filename.lower() in ("readme", "license", "changelog", "pixpin_2025-11-12_01-43-20"):
                    continue
                keywords = _extract_all_keywords(filename)
                if keywords:
                    logos.append((keywords, logo_file))
    
    # Sort by longest keyword length (descending) for more specific matching first
    logos.sort(key=lambda x: max(len(k) for k in x[0]) if x[0] else 0, reverse=True)
    
    _available_logos_cache = logos
    log.info(f"Scanned {len(logos)} logo files from {LOGOS_DIR}")
    return logos


def _extract_model_info(model_id: str) -> dict:
    """
    Extract structured information from a model ID.
    
    Handles various formats:
    - "openai/gpt-5.2" -> provider="openai", model="gpt-5.2"
    - "OpenRouter.openai/gpt-5.2" -> service="openrouter", provider="openai", model="gpt-5.2"
    - "OpenRouter.qwen/qwen3-235b-a22b:free" -> service="openrouter", provider="qwen", model="qwen3-235b-a22b"
    - "gpt-4o-mini" -> model="gpt-4o-mini"
    """
    model_id_lower = model_id.lower()
    info = {"original": model_id, "model": model_id_lower, "provider": None, "service": None}
    
    # Check for service.provider/model pattern (e.g., OpenRouter.openai/gpt-5.2)
    service_match = re.match(r'^([a-z]+)\.([a-z]+)/(.+)$', model_id_lower)
    if service_match:
        info["service"] = service_match.group(1)
        info["provider"] = service_match.group(2)
        info["model"] = service_match.group(3)
    else:
        # Check for provider/model pattern (e.g., openai/gpt-5.2)
        provider_match = re.match(r'^([a-z]+)/(.+)$', model_id_lower)
        if provider_match:
            info["provider"] = provider_match.group(1)
            info["model"] = provider_match.group(2)
    
    # Clean up model name - remove suffixes like :free, :latest
    info["model_clean"] = re.sub(r':[a-z]+$', '', info["model"])
    
    return info


def _match_logo_for_model(model_id: str) -> Optional[Path]:
    """
    Find a matching logo for a model ID using smart prioritized matching.
    
    Matching priority:
    1. Exact model name match (e.g., "gpt-5.2" -> "gpt-5.2.png")
    2. Model name with version variations (e.g., "gpt-5.2" matches "gpt-5.2-pro.png")
    3. Provider-based match (e.g., "openai" -> "openai.png") 
    4. Fuzzy keyword match
    """
    info = _extract_model_info(model_id)
    model_name = info["model_clean"]
    provider = info["provider"]
    model_id_lower = model_id.lower()
    
    # Special case: Gemini image models -> nana-banana
    if "gemini" in model_id_lower and "image" in model_id_lower:
        for logo_keywords, logo_path in _scan_available_logos():
            if any("nana" in k and "banana" in k for k in logo_keywords):
                return logo_path
            if "nana" in logo_keywords and "banana" in logo_keywords:
                return logo_path
    
    logos = _scan_available_logos()
    candidates = []  # List of (score, logo_path)
    
    for logo_keywords, logo_path in logos:
        logo_stem = logo_path.stem.lower()
        logo_stem_normalized = _normalize_name(logo_stem)
        score = 0
        
        # === EXACT MATCH (Highest Priority) ===
        # Check if logo filename exactly matches model name
        if logo_stem_normalized == model_name or logo_stem == model_name:
            score = 1000
        # Check if logo filename starts with model name (e.g., gpt-5.2 matches gpt-5.2-pro)
        elif logo_stem_normalized.startswith(model_name) or logo_stem.startswith(model_name):
            score = 900
        # Check if model name starts with logo filename (e.g., gpt-5.2-xyz matches gpt-5.2)
        elif model_name.startswith(logo_stem_normalized) or model_name.startswith(logo_stem):
            # Length bonus - longer matches are better
            score = 800 + len(logo_stem_normalized) * 10
        
        # === PROVIDER MATCH ===
        # If provider matches (e.g., "openai" matches "openai.png" or "openai_(3).jpg")
        if provider and score == 0:
            if provider in logo_keywords or provider == logo_stem_normalized:
                score = 500
            # Check if provider is in logo filename
            elif provider in logo_stem:
                score = 400
        
        # === BRAND KEYWORD MATCH ===
        # Check for important brand keywords in model name
        brand_keywords = ["qwen", "claude", "gemini", "deepseek", "grok", "llama", "mistral", 
                         "meta", "google", "anthropic", "kimi", "moonshot", "doubao", "zhipu",
                         "glm", "hunyuan", "minimax", "copilot", "gemma", "baai", "bytedance"]
        
        if score == 0:
            for brand in brand_keywords:
                if brand in model_name or brand in model_id_lower:
                    if brand in logo_keywords or brand in logo_stem_normalized:
                        score = 700 + len(brand) * 5
                        break
        
        # === FUZZY MATCH (Low Priority) ===
        if score == 0:
            model_keywords = set(re.split(r'[-_\.:/\s]+', model_name))
            for logo_kw in logo_keywords:
                if len(logo_kw) >= 4:  # Only meaningful keywords
                    for model_kw in model_keywords:
                        if len(model_kw) >= 4:
                            if model_kw == logo_kw:
                                score = 300 + len(model_kw) * 5
                                break
                            elif model_kw in logo_kw or logo_kw in model_kw:
                                score = 200 + min(len(model_kw), len(logo_kw)) * 3
                                break
                    if score > 0:
                        break
        
        # Avoid matching generic service names like "openrouter" unless nothing else matches
        if score > 0 and score < 500:
            generic_names = ["openrouter", "newapi", "one", "api"]
            if any(g in logo_stem_normalized for g in generic_names):
                score = max(0, score - 300)  # Heavily penalize generic matches
        
        if score > 0:
            candidates.append((score, logo_path))
    
    if candidates:
        # Return the highest scoring match
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_path = candidates[0]
        log.debug(f"Logo match scores for '{model_id}': top={best_score}, path={best_path.name}")
        return best_path
    
    return None


def get_logo_path(model_id: str) -> Optional[Path]:
    """
    Get the filesystem path to the logo for a given model ID.
    
    This function uses SMART FUZZY MATCHING:
    - "FreeDuck.claude-3-5-haiku" matches "claude-color.svg" ✓
    - "gemini-3-pro-preview" matches "Google-gemini-icon.svg" ✓
    - "qwen/qwen-image(free)" matches "qwen-color (1).png" ✓
    - "deepseek-r1:8b" matches "deepseek-color (1).png" ✓
    - "gemini-3-pro-image-preview" matches "nana banana.jpg" ✓
    """
    # Check cache first
    if model_id in _logo_cache:
        cached = _logo_cache[model_id]
        return Path(cached) if cached else None
    
    # Find matching logo
    logo_path = _match_logo_for_model(model_id)
    
    if logo_path:
        _logo_cache[model_id] = str(logo_path)
        log.debug(f"Logo matched: '{model_id}' -> {logo_path.name}")
        return logo_path
    
    _logo_cache[model_id] = None
    return None


def get_logo_bytes(model_id: str) -> Optional[tuple[bytes, str]]:
    """Read and return the logo bytes for a given model ID."""
    logo_path = get_logo_path(model_id)
    if not logo_path:
        return None
    
    try:
        content = logo_path.read_bytes()
        ext = logo_path.suffix.lower()
        content_types = {
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return (content, content_types.get(ext, "image/png"))
    except Exception as e:
        log.error(f"Failed to read logo file {logo_path}: {e}")
        return None


def clear_cache():
    """Clear all caches. Call after adding new logo files."""
    global _logo_cache, _available_logos_cache
    _logo_cache = {}
    _available_logos_cache = None
    log.info("Logo cache cleared")


def list_available_logos() -> list[str]:
    """List all available logo files."""
    return [str(path.name) for _, path in _scan_available_logos()]


def get_brand_for_model(model_id: str) -> Optional[str]:
    """Get the brand/logo name for a model ID."""
    logo_path = get_logo_path(model_id)
    return logo_path.stem if logo_path else None
