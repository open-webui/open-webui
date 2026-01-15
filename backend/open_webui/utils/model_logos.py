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
from functools import lru_cache
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
    
    # Only cache if we found logos OR the directory doesn't exist
    # This prevents caching empty results during startup race conditions
    if logos or not LOGOS_DIR.exists():
        _available_logos_cache = logos
        log.info(f"Scanned {len(logos)} logo files from {LOGOS_DIR}")
    else:
        log.warning(f"No logos found in {LOGOS_DIR}, not caching to allow retry")
    
    return logos


def _extract_model_info(model_id: str) -> dict:
    """
    Extract structured information from a model ID.
    
    Handles various formats:
    - "openai/gpt-5.2" -> provider="openai", model="gpt-5.2"
    - "OpenRouter.openai/gpt-5.2" -> service="openrouter", provider="openai", model="gpt-5.2"
    - "OpenRouter.qwen/qwen3-235b-a22b:free" -> service="openrouter", provider="qwen", model="qwen3-235b-a22b"
    - "openai.gpt-5.1-2025-11-13" -> prefix="openai", model="gpt-5.1-2025-11-13"
    - "gpt-4o-mini" -> model="gpt-4o-mini"
    """
    model_id_lower = model_id.lower()
    info = {"original": model_id, "model": model_id_lower, "provider": None, "service": None, "prefix": None}
    
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
        else:
            # Check for prefix.model pattern (e.g., openai.gpt-5.1-2025-11-13)
            # prefix is a short word (max 20 chars), followed by . and then the model name
            prefix_match = re.match(r'^([a-z][a-z0-9_-]{0,19})\.(.+)$', model_id_lower)
            if prefix_match:
                prefix = prefix_match.group(1)
                model_part = prefix_match.group(2)
                # Only treat as prefix if the prefix is a known provider/service name
                # or if the model part looks like a standard model name
                known_prefixes = {"openai", "anthropic", "google", "gemini", "claude", "meta", 
                                  "cohere", "huggingface", "mistral", "together", "anyscale",
                                  "perplexity", "groq", "fireworks", "deepinfra", "openrouter",
                                  "azure", "aws", "bedrock", "vertex", "siliconflow", "alibaba",
                                  "bytedance", "baidu", "tencent", "zhipu", "moonshot", "minimax",
                                  "stepfun", "yi", "doubao", "kimi", "deepseek", "qwen", "hotaru"}
                if prefix in known_prefixes:
                    info["prefix"] = prefix
                    info["model"] = model_part
    
    # Clean up model name - remove suffixes like :free, :latest
    info["model_clean"] = re.sub(r':[a-z]+$', '', info["model"])
    
    return info


def _match_logo_for_model(model_id: str) -> Optional[Path]:
    """
    Find a matching logo for a model ID using smart prioritized matching.
    
    Matching priority:
    1. Exact match
    2. Logo is a full component of model ID (e.g., "Hotaru.gpt-5.1" contains "gpt-5.1")
    3. Model starts with logo (e.g., "gpt-5.1-preview" starts with "gpt-5.1")
    4. Model ID ends with logo (e.g., "openai/gpt-5.2" ends with "gpt-5.2")
    5. Brand keyword matching
    6. Fuzzy matching
    """
    info = _extract_model_info(model_id)
    model_name_extracted = info["model_clean"]
    provider = info["provider"]
    model_id_lower = model_id.lower()
    
    # Special case: Gemini image models -> nano-banana
    if "gemini" in model_id_lower and "image" in model_id_lower:
        for logo_keywords, logo_path in _scan_available_logos():
            if any("nano" in k and "banana" in k for k in logo_keywords):
                return logo_path
            if "nano" in logo_keywords and "banana" in logo_keywords:
                return logo_path
    
    logos = _scan_available_logos()
    candidates = []  # List of (score, logo_path)
    
    # Pre-calculate delimiters for boundary checks
    delimiters = set(".-_/: ")
    
    for logo_keywords, logo_path in logos:
        logo_stem = logo_path.stem.lower()
        logo_stem_normalized = _normalize_name(logo_stem)
        score = 0
        
        # === EXACT MODEL NAME MATCH (Highest Priority) ===
        # If logo filename precisely matches the extracted model name, give highest score
        # e.g., "gpt-oss-120b.png" matches model_name "gpt-oss-120b" from "OpenRouter.openai/gpt-oss-120b:free"
        if logo_stem_normalized == model_name_extracted or logo_stem == model_name_extracted:
            score = 1000
            candidates.append((score, logo_path))
            continue  # Skip other matching for this logo, we have the best match
        
        # Candidate strings to match against (original and normalized logo names)
        check_logos = {logo_stem}
        if logo_stem_normalized != logo_stem:
            check_logos.add(logo_stem_normalized)
            
        for check_logo in check_logos:
            if not check_logo or len(check_logo) < 2:
                continue
                
            # === STRICT SUBSTRING MATCHING ===
            # We look for the logo name inside the model ID and check boundaries
            
            try:
                # Find all occurrences
                start_indices = [m.start() for m in re.finditer(re.escape(check_logo), model_id_lower)]
                
                for start_idx in start_indices:
                    end_idx = start_idx + len(check_logo)
                    
                    # Check Left Boundary
                    # Valid if at start of string OR preceded by a delimiter
                    left_ok = (start_idx == 0) or (model_id_lower[start_idx-1] in delimiters)
                    
                    # Check Right Boundary
                    # Valid if at end of string OR followed by a delimiter (or followed by digit? sometimes generic)
                    right_ok = (end_idx == len(model_id_lower)) or (model_id_lower[end_idx] in delimiters)
                    
                    # 1. EXACT TOKEN MATCH: "Hotaru.gpt-5.1" matches "gpt-5.1"
                    # "start.gpt-5.1.end" -> Both boundaries OK
                    if left_ok and right_ok:
                        s = 900 + len(check_logo)  # Base 900 + length bonus
                        # Boost if it's the very end (suffix match) - likely the model name
                        if end_idx == len(model_id_lower):
                            s += 20
                        # Boost if it's the very start
                        if start_idx == 0:
                            s += 30
                        score = max(score, s)
                        
                    # 2. PREFIX TOKEN MATCH: "gpt-5.1-preview" matches "gpt-5.1"
                    # Left OK, Right NOT OK (but right is likely version info)
                    elif left_ok and not right_ok:
                        # Only valid if not part of a larger word?
                        # e.g. "gpt-5.1" in "gpt-5.10" -> Right char is '0'. Not a delimiter.
                        # We want to avoid matching "gpt-4" in "gpt-40"
                        next_char = model_id_lower[end_idx]
                        if not next_char.isalnum(): # It is a delimiter
                             score = max(score, 900)
                        else:
                             # It continues with alphanumeric.
                             # e.g. "gpt-5.1" in "gpt-5.12"
                             # Should we match? Maybe lower score.
                             if check_logo[-1].isdigit() and next_char.isdigit():
                                 # Matching "gpt-4" in "gpt-40". BAD.
                                 pass 
                             else:
                                 score = max(score, 800)
            except Exception:
                pass
        
        # === PROVIDER MATCH ===
        if provider and score < 500:
            if provider in logo_keywords or provider == logo_stem_normalized:
                score = max(score, 500)
            elif provider in logo_stem:
                score = max(score, 400)
        
        # === BRAND KEYWORD MATCH ===
        # Important for models like "qwen-plus" matching "qwen" logo
        brand_keywords = ["qwen", "claude", "gemini", "deepseek", "grok", "llama", "mistral", 
                         "meta", "google", "anthropic", "kimi", "moonshot", "doubao", "zhipu",
                         "glm", "hunyuan", "minimax", "copilot", "gemma", "baai", "bytedance"]
        
        if score < 700:
            for brand in brand_keywords:
                if brand in model_id_lower:
                    # Check if logo represents this brand
                    if brand in logo_keywords or brand in logo_stem_normalized:
                        # Give a solid score, but lower than specific model matches
                        score = max(score, 700 + len(brand))
                        break
        
        # === REVERSE SUBSTRING MATCH (Fallback) ===
        # Ensure "gpt5" matches "gpt-5-chat-latest" or "gpt-5.png"
        if score < 650:
            # Create delimiter-free versions for loose comparison
            model_simple = re.sub(r'[-_\.:/\s]+', '', model_id_lower)
            logo_simple = re.sub(r'[-_\.:/\s]+', '', logo_stem.lower())
            
            # Avoid matching very short generic strings (e.g. "v1", "gpt")
            if len(model_simple) >= 3:
                # Check if model is contained in logo (e.g., "gpt5" in "gpt5chatlatest")
                if model_simple in logo_simple:
                    # Penalize if logo is much longer than model (avoid matching "gpt" to "gpt-4-turbo-32k")
                    length_diff = len(logo_simple) - len(model_simple)
                    base_score = 600
                    final_score = base_score - (length_diff * 5)
                    score = max(score, max(400, final_score))
        
        # Avoid matching generic service names like "openrouter" unless nothing else matches
        if score > 0 and score < 500:
            generic_names = ["openrouter", "newapi", "one", "api"]
            if any(g in logo_stem_normalized for g in generic_names):
                score = max(0, score - 300)
        
        if score > 0:
            candidates.append((score, logo_path))
    
    if candidates:
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
    
    # Only cache None if we have a valid logo scan
    # This prevents permanently caching failures during startup
    if _available_logos_cache is not None:
        _logo_cache[model_id] = None
        log.debug(f"No logo match for '{model_id}', cached as None")
    else:
        log.debug(f"No logo match for '{model_id}', not caching (logos not loaded)")
    
    return None


def get_logo_bytes(model_id: str) -> Optional[tuple[bytes, str]]:
    """Read and return the logo bytes for a given model ID."""
    logo_path = get_logo_path(model_id)
    if not logo_path:
        return None
    return _read_logo_file_cached(str(logo_path))


@lru_cache(maxsize=100)
def _read_logo_file_cached(logo_path_str: str) -> Optional[tuple[bytes, str]]:
    """
    Cached file read for logo bytes.
    Uses LRU cache to avoid repeated disk I/O for frequently accessed logos.
    """
    logo_path = Path(logo_path_str)
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
    _read_logo_file_cached.cache_clear()  # Clear LRU cache for file bytes
    log.info("Logo cache cleared (including LRU file cache)")


def list_available_logos() -> list[str]:
    """List all available logo files."""
    return [str(path.name) for _, path in _scan_available_logos()]


def get_brand_for_model(model_id: str) -> Optional[str]:
    """Get the brand/logo name for a model ID."""
    logo_path = get_logo_path(model_id)
    return logo_path.stem if logo_path else None
