"""
Model Logo Auto-Loading Utility

This module provides DYNAMIC automatic logo matching for LLM models.
It scans the static/model_logos directory and matches logo filenames
against model IDs using smart fuzzy matching.

HOW IT WORKS:
1. Scans all logo files in static/model_logos/ directory
2. Cleans filenames (removes -color, spaces, (1), etc.)
3. Uses bidirectional "contains" matching for flexibility
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
_available_logos_cache: Optional[list[tuple[str, str, Path]]] = None


def _normalize_name(name: str) -> str:
    """
    Normalize a name for matching by removing common suffixes and cleaning up.
    
    Examples:
        "claude-color" -> "claude"
        "deepseek-color (1)" -> "deepseek"
        "nana banana" -> "nana-banana" or "nanabanana"
        "qwen-color (1)" -> "qwen"
    """
    name = name.lower().strip()
    
    # Replace spaces with hyphens for matching
    name = name.replace(" ", "-")
    
    # Remove common suffixes like -color, -icon, -logo
    name = re.sub(r'[-_]?(color|icon|logo|brand|official)$', '', name)
    
    # Remove version numbers like (1), (2), _v2, -v1
    name = re.sub(r'[-_\s]?\(\d+\)$', '', name)
    name = re.sub(r'[-_]?v\d+$', '', name)
    
    # Remove trailing hyphens/underscores
    name = name.rstrip('-_')
    
    return name


def _extract_keywords(name: str) -> list[str]:
    """
    Extract multiple keyword variants from a name for flexible matching.
    
    Examples:
        "claude-color" -> ["claude-color", "claude", "claudecolor"]
        "nana banana" -> ["nana-banana", "nana", "banana", "nanabanana"]
    """
    keywords = []
    
    # Original name (lowercase)
    original = name.lower().strip()
    keywords.append(original)
    
    # Normalized version
    normalized = _normalize_name(original)
    if normalized and normalized != original:
        keywords.append(normalized)
    
    # Version without hyphens (for matching)
    no_hyphens = original.replace("-", "").replace("_", "").replace(" ", "")
    if no_hyphens and no_hyphens not in keywords:
        keywords.append(no_hyphens)
    
    # Split by common delimiters and add parts
    parts = re.split(r'[-_\s]+', original)
    for part in parts:
        if len(part) >= 3 and part not in keywords:  # Only meaningful parts
            keywords.append(part)
    
    return keywords


def _scan_available_logos() -> list[tuple[str, str, Path]]:
    """
    Scan the logos directory and return all available logo files.
    
    Returns:
        List of (original_name, normalized_name, logo_path) tuples,
        sorted by normalized name length (longest first) for more specific matching.
    """
    global _available_logos_cache
    
    if _available_logos_cache is not None:
        return _available_logos_cache
    
    logos = []
    if LOGOS_DIR.exists():
        for ext in SUPPORTED_EXTENSIONS:
            for logo_file in LOGOS_DIR.glob(f"*{ext}"):
                original_name = logo_file.stem.lower()
                # Skip README and other non-logo files
                if original_name in ("readme", "license", "changelog"):
                    continue
                normalized_name = _normalize_name(original_name)
                logos.append((original_name, normalized_name, logo_file))
    
    # Sort by normalized name length (descending) for more specific matching first
    # e.g., "gpt-5-mini" should match before "gpt-5"
    logos.sort(key=lambda x: len(x[1]), reverse=True)
    
    _available_logos_cache = logos
    log.info(f"Scanned {len(logos)} logo files from {LOGOS_DIR}")
    return logos


def _match_logo_for_model(model_id: str) -> Optional[Path]:
    """
    Find a matching logo for a model ID using smart fuzzy matching.
    
    Matching strategies (in order):
    1. Exact match: logo filename == model_id
    2. Logo in model: logo filename is contained in model_id
    3. Model in logo: model_id keyword is contained in logo filename
    4. Normalized matching: compare cleaned versions
    
    Args:
        model_id: The model identifier (e.g., "gpt-4o-mini", "claude-3-opus")
    
    Returns:
        Path to the matching logo file, or None if no match
    """
    model_id_lower = model_id.lower()
    model_normalized = _normalize_name(model_id_lower)
    model_no_delimiters = model_id_lower.replace("-", "").replace("_", "").replace(".", "")
    
    # Special case: Gemini image models -> nana-banana
    if "gemini" in model_id_lower and "image" in model_id_lower:
        for orig, norm, logo_path in _scan_available_logos():
            # Match "nana banana", "nana-banana", or "nanabanana"
            if "nana" in norm and "banana" in norm:
                return logo_path
            if "nana" in orig and "banana" in orig:
                return logo_path
    
    logos = _scan_available_logos()
    
    # Strategy 1 & 2: Check if logo name (original or normalized) is in model_id
    for orig, norm, logo_path in logos:
        # Exact or contains match with normalized name
        if norm in model_id_lower or norm in model_normalized:
            return logo_path
        # Also check original name
        if orig in model_id_lower:
            return logo_path
    
    # Strategy 3: Check if model keywords are in logo name (reverse matching)
    # This helps match "FreeDuck.claude-3-5-haiku" with "claude-color.svg"
    model_keywords = _extract_keywords(model_id_lower)
    for orig, norm, logo_path in logos:
        for keyword in model_keywords:
            if len(keyword) >= 4:  # Only check meaningful keywords
                if keyword in norm or keyword in orig:
                    return logo_path
    
    # Strategy 4: Check without delimiters
    for orig, norm, logo_path in logos:
        logo_no_delimiters = norm.replace("-", "").replace("_", "")
        if logo_no_delimiters in model_no_delimiters:
            return logo_path
        if model_no_delimiters and logo_no_delimiters and \
           (model_no_delimiters in logo_no_delimiters or logo_no_delimiters in model_no_delimiters):
            return logo_path
    
    return None


def get_logo_path(model_id: str) -> Optional[Path]:
    """
    Get the filesystem path to the logo for a given model ID.
    
    This function uses SMART FUZZY MATCHING:
    - "FreeDuck.claude-3-5-haiku" matches "claude-color.svg" ✓
    - "gemini-3-pro-image-preview" matches "nana banana.jpg" ✓
    - "776-gpt-5-mini-abc" matches "gpt-5-mini.png" ✓
    - "deepseek-chat-v2" matches "deepseek-color (1).png" ✓
    
    Args:
        model_id: The model identifier
    
    Returns:
        Path to the logo file, or None if no matching logo exists
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
    """List all available logo names."""
    return [norm for _, norm, _ in _scan_available_logos()]


def get_brand_for_model(model_id: str) -> Optional[str]:
    """Get the brand/logo name for a model ID."""
    logo_path = get_logo_path(model_id)
    return logo_path.stem if logo_path else None
