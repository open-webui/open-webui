"""
Temporary File Cleanup Utility

Manages temporary file caching with size limits to prevent /tmp overflow.
Critical for Render deployments with 2GB /tmp limit.

Features:
- Periodic cleanup of stale temp files
- Total cache size limit enforcement
- Age-based expiration (default: 30 minutes)
- Safe cleanup with error handling

Configuration (environment variables):
- TEMP_CLEANUP_INTERVAL_MINUTES: How often cleanup runs (default: 5)
- TEMP_CLEANUP_MAX_AGE_MINUTES: Delete files older than this (default: 30)
- TEMP_CLEANUP_MAX_SIZE_MB: Max total cache size (default: 500)
"""

import asyncio
import glob
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))

# Configuration defaults (can be overridden by environment variables)
DEFAULT_MAX_CACHE_SIZE_MB = 500
DEFAULT_MAX_AGE_MINUTES = 30
DEFAULT_CLEANUP_INTERVAL_MINUTES = 5

# File patterns to clean up (Open WebUI specific)
CLEANUP_PATTERNS = [
    "segment_*.mp3",  # Audio segments from audio.py
    "video_segment_*.mp4",  # Video segments from audio.py
    "stream_*.mp4",  # Video streaming cache from files.py
    "gmail_att_*",  # Gmail attachment temp files
]


def _get_config_values() -> Tuple[int, int, int]:
    """
    Get cleanup config values with lazy import to avoid circular imports.

    Returns:
        Tuple of (interval_minutes, max_age_minutes, max_size_mb)
    """
    try:
        from open_webui.config import (
            TEMP_CLEANUP_INTERVAL_MINUTES,
            TEMP_CLEANUP_MAX_AGE_MINUTES,
            TEMP_CLEANUP_MAX_SIZE_MB,
        )

        return (
            TEMP_CLEANUP_INTERVAL_MINUTES,
            TEMP_CLEANUP_MAX_AGE_MINUTES,
            TEMP_CLEANUP_MAX_SIZE_MB,
        )
    except ImportError:
        return (
            DEFAULT_CLEANUP_INTERVAL_MINUTES,
            DEFAULT_MAX_AGE_MINUTES,
            DEFAULT_MAX_CACHE_SIZE_MB,
        )


def get_temp_dir() -> Path:
    """Get the system temp directory path."""
    return Path(tempfile.gettempdir())


def get_cache_files(patterns: List[str] = CLEANUP_PATTERNS) -> List[Tuple[Path, float, int]]:
    """
    Get all cache files matching patterns with their modification time and size.

    Returns:
        List of (path, mtime, size) tuples sorted by mtime (oldest first)
    """
    temp_dir = get_temp_dir()
    files = []

    for pattern in patterns:
        for filepath in glob.glob(str(temp_dir / pattern)):
            try:
                path = Path(filepath)
                if path.is_file():
                    stat = path.stat()
                    files.append((path, stat.st_mtime, stat.st_size))
            except (OSError, FileNotFoundError):
                # File may have been deleted between glob and stat
                continue

    # Sort by modification time (oldest first)
    files.sort(key=lambda x: x[1])
    return files


def get_total_cache_size(patterns: List[str] = CLEANUP_PATTERNS) -> int:
    """Get total size of cache files in bytes."""
    return sum(size for _, _, size in get_cache_files(patterns))


def run_cleanup(
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    max_size_mb: int = DEFAULT_MAX_CACHE_SIZE_MB,
    patterns: List[str] = CLEANUP_PATTERNS,
) -> Dict:
    """
    Run full cleanup: age-based first, then size-based.

    Args:
        max_age_minutes: Delete files older than this
        max_size_mb: Maximum total cache size allowed
        patterns: File patterns to clean up

    Returns:
        Dict with cleanup statistics
    """
    start_time = time.time()
    max_size_bytes = max_size_mb * 1024 * 1024
    cutoff_time = time.time() - (max_age_minutes * 60)

    # Get initial state (single scan)
    files = get_cache_files(patterns)
    initial_count = len(files)
    initial_size = sum(size for _, _, size in files)

    files_deleted = 0
    bytes_freed = 0
    remaining_files = []

    # Phase 1: Delete old files
    for path, mtime, size in files:
        if mtime < cutoff_time:
            try:
                path.unlink()
                files_deleted += 1
                bytes_freed += size
                log.debug(f"Cleaned up old temp file: {path.name}")
            except (OSError, FileNotFoundError) as e:
                log.warning(f"Failed to delete temp file {path}: {e}")
                remaining_files.append((path, mtime, size))
        else:
            remaining_files.append((path, mtime, size))

    # Phase 2: Enforce size limit on remaining files
    current_size = sum(size for _, _, size in remaining_files)

    if current_size > max_size_bytes:
        # Files are already sorted oldest-first
        for path, mtime, size in remaining_files:
            if current_size <= max_size_bytes:
                break
            try:
                path.unlink()
                files_deleted += 1
                bytes_freed += size
                current_size -= size
                log.debug(f"Cleaned up temp file for size limit: {path.name}")
            except (OSError, FileNotFoundError) as e:
                log.warning(f"Failed to delete temp file {path}: {e}")

    elapsed = time.time() - start_time
    final_size = initial_size - bytes_freed
    final_count = initial_count - files_deleted

    result = {
        "initial_files": initial_count,
        "initial_size_mb": initial_size / (1024 * 1024),
        "final_files": final_count,
        "final_size_mb": final_size / (1024 * 1024),
        "files_deleted": files_deleted,
        "bytes_freed": bytes_freed,
        "bytes_freed_mb": bytes_freed / (1024 * 1024),
        "elapsed_seconds": elapsed,
    }

    if files_deleted > 0:
        log.info(
            f"🧹 Temp cleanup: deleted {files_deleted} files, "
            f"freed {result['bytes_freed_mb']:.1f} MB "
            f"(now: {final_count} files, {result['final_size_mb']:.1f} MB)"
        )

    return result


async def periodic_temp_cleanup(
    cleanup_interval_minutes: int = None,
    max_age_minutes: int = None,
    max_size_mb: int = None,
):
    """
    Background task that periodically cleans up temp files.

    Should be started in the application lifespan.
    Uses config values from environment variables if not specified.
    """
    # Load config values (with defaults if config not available)
    cfg_interval, cfg_age, cfg_size = _get_config_values()

    cleanup_interval_minutes = cleanup_interval_minutes or cfg_interval
    max_age_minutes = max_age_minutes or cfg_age
    max_size_mb = max_size_mb or cfg_size

    log.info(
        f"🧹 Temp cleanup scheduler started "
        f"(interval: {cleanup_interval_minutes}min, max_age: {max_age_minutes}min, "
        f"max_size: {max_size_mb}MB)"
    )

    # Initial cleanup on startup
    await asyncio.sleep(10)  # Wait for app to fully initialize

    try:
        run_cleanup(max_age_minutes, max_size_mb)
    except Exception as e:
        log.error(f"Initial temp cleanup failed: {e}")

    # Periodic cleanup
    while True:
        try:
            await asyncio.sleep(cleanup_interval_minutes * 60)
            run_cleanup(max_age_minutes, max_size_mb)
        except asyncio.CancelledError:
            log.info("🧹 Temp cleanup scheduler shutting down")
            break
        except Exception as e:
            log.error(f"Temp cleanup error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


def ensure_cache_space(required_mb: int = 50, max_size_mb: int = DEFAULT_MAX_CACHE_SIZE_MB) -> bool:
    """
    Ensure there's enough space for a new cache entry.
    Call this before creating large temp files.

    Args:
        required_mb: Space needed in MB
        max_size_mb: Maximum total cache size

    Returns:
        True if space is available or was freed, False if cleanup failed
    """
    current_size_mb = get_total_cache_size() / (1024 * 1024)

    if current_size_mb + required_mb <= max_size_mb:
        return True

    log.info(
        f"Cache space check: need {required_mb}MB, " f"have {current_size_mb:.1f}/{max_size_mb}MB - running cleanup"
    )

    # Aggressive cleanup to make room
    target_size_mb = max(0, max_size_mb - required_mb)
    result = run_cleanup(max_age_minutes=15, max_size_mb=target_size_mb)  # More aggressive age limit

    return result["final_size_mb"] + required_mb <= max_size_mb


def get_cache_stats() -> Dict:
    """Get current cache statistics for monitoring."""
    files = get_cache_files()

    if not files:
        return {
            "file_count": 0,
            "total_size_mb": 0,
            "oldest_file_age_minutes": 0,
            "newest_file_age_minutes": 0,
        }

    now = time.time()
    sizes = [size for _, _, size in files]
    mtimes = [mtime for _, mtime, _ in files]

    return {
        "file_count": len(files),
        "total_size_mb": sum(sizes) / (1024 * 1024),
        "oldest_file_age_minutes": (now - min(mtimes)) / 60 if mtimes else 0,
        "newest_file_age_minutes": (now - max(mtimes)) / 60 if mtimes else 0,
    }
