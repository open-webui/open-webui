"""
Model Logo Auto-Loading Utility

This module provides DYNAMIC automatic logo matching for LLM models.
It scans the static/model_logos directory and matches logo filenames
against model IDs using "contains" logic.

HOW IT WORKS:
1. Scans all logo files in static/model_logos/ directory
2. Sorts filenames by length (longest first for specificity)
3. If a model ID contains a logo filename, that logo is used
4. No need to modify code when adding new logos - just drop the file!

This is a custom enhancement that minimizes merge conflicts with upstream
by isolating all logic in this new file.
"""

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
_available_logos_cache: Optional[list[tuple[str, Path]]] = None


def _scan_available_logos() -> list[tuple[str, Path]]:
    """
    Scan the logos directory and return all available logo files.
    
    Returns:
        List of (logo_name, logo_path) tuples, sorted by name length (longest first)
        for more specific matching.
    """
    global _available_logos_cache
    
    if _available_logos_cache is not None:
        return _available_logos_cache
    
    logos = []
    if LOGOS_DIR.exists():
        for ext in SUPPORTED_EXTENSIONS:
            for logo_file in LOGOS_DIR.glob(f"*{ext}"):
                logo_name = logo_file.stem.lower()  # filename without extension
                # Skip README and other non-logo files
                if logo_name in ("readme", "license", "changelog"):
                    continue
                logos.append((logo_name, logo_file))
    
    # Sort by name length (descending) for more specific matching first
    # e.g., "gpt-5-mini" should match before "gpt-5"
    logos.sort(key=lambda x: len(x[0]), reverse=True)
    
    _available_logos_cache = logos
    log.info(f"Scanned {len(logos)} logo files from {LOGOS_DIR}")
    return logos


def _match_logo_for_model(model_id: str) -> Optional[Path]:
    """
    Find a matching logo for a model ID by scanning available logos.
    
    The matching uses "contains" logic - if the model ID contains the logo
    filename anywhere, it's a match. Longer filenames are checked first
    for more specific matching.
    
    Args:
        model_id: The model identifier (e.g., "gpt-4o-mini", "claude-3-opus")
    
    Returns:
        Path to the matching logo file, or None if no match
    """
    model_id_lower = model_id.lower()
    
    # Special case: Gemini image models -> nana-banana
    if "gemini" in model_id_lower and "image" in model_id_lower:
        for logo_name, logo_path in _scan_available_logos():
            if logo_name == "nana-banana":
                return logo_path
    
    # Scan all available logos (sorted by length for specificity)
    for logo_name, logo_path in _scan_available_logos():
        if logo_name in model_id_lower:
            return logo_path
    
    return None


def get_logo_path(model_id: str) -> Optional[Path]:
    """
    Get the filesystem path to the logo for a given model ID.
    
    This function uses DYNAMIC directory scanning - just add logo files
    to the static/model_logos directory and they'll be automatically matched.
    
    Matching rules:
    1. Model ID is converted to lowercase
    2. Logo filename (without extension) is matched using "contains"
    3. Longer filenames match first (e.g., "gpt-5-mini" before "gpt-5")
    4. Special: gemini + image -> nana-banana
    
    Examples:
        "gpt-4o-mini" -> matches "gpt-4o-mini.png" (exact)
        "776-gpt-5-mini-abc" -> matches "gpt-5-mini.png" (contains)
        "my-custom-deepseek-v2" -> matches "deepseek.png" (contains)
        "gemini-2.0-flash-image-gen" -> matches "nana-banana.png" (special)
    
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
    """
    Clear all caches. Call this after adding new logo files to the directory.
    The cache will be automatically refreshed on next logo lookup.
    """
    global _logo_cache, _available_logos_cache
    _logo_cache = {}
    _available_logos_cache = None
    log.info("Logo cache cleared")


def list_available_logos() -> list[str]:
    """
    List all available logo names (filenames without extensions).
    Useful for debugging and admin interfaces.
    """
    return [name for name, _ in _scan_available_logos()]


def get_brand_for_model(model_id: str) -> Optional[str]:
    """
    Get the brand/logo name for a model ID.
    This is a convenience function that returns just the logo name.
    
    Args:
        model_id: The model identifier
    
    Returns:
        Logo name (filename without extension) or None if no match
    """
    logo_path = get_logo_path(model_id)
    if logo_path:
        return logo_path.stem
    return None
