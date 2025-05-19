"""
API Key Selection Utility

This module provides functions for selecting API keys based on different strategies.
It's designed to work with the API key management system in the UI.

Available strategies:
- Random: Selects a random key for each request
- Round Robin: Cycles through keys in sequence
- Least Recently Used: Selects the key that was used least recently
- Weighted: Selects keys based on their assigned weights
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional

from open_webui.env import SRC_LOG_LEVELS

# Configure logging
logger = logging.getLogger("api_key_selection")
logger.setLevel(SRC_LOG_LEVELS.get("API_KEY_SELECTION", logging.DEBUG))


def mask_api_key(key: str) -> str:
    """
    Mask an API key for logging purposes.

    Args:
        key: The API key to mask

    Returns:
        A masked version of the key (e.g., "sk_12...3456")
    """
    if not key or len(key) < 8:
        return "****"

    return f"{key[:4]}...{key[-4:]}"


# Key selection strategies
class KeySelectionStrategy:
    """Enum-like class for API key selection strategies"""

    RANDOM = "random"
    ROUND_ROBIN = "round-robin"
    LEAST_RECENTLY_USED = "least-recently-used"
    WEIGHTED = "weighted"


# In-memory cache for API keys
_api_key_cache: Dict[str, Dict[str, Any]] = {}


def select_api_key(
    connection_id: str, keys: List[str], options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Select an API key from a list of keys based on the specified strategy

    Args:
        connection_id: Unique identifier for the connection (used for caching)
        keys: Array of API keys to select from
        options: Options for key selection including:
            - strategy: Selection strategy (random, round-robin, least-recently-used, weighted)
            - enable_cache: Whether to use caching (default: True)
            - cache_ttl: Cache time-to-live in seconds (default: 300)
            - validate_key: Optional function to validate keys
            - weights: Key weights for weighted distribution

    Returns:
        The selected API key

    Raises:
        ValueError: If no valid API keys are available
    """
    if not options:
        options = {}

    # Validate inputs
    if not connection_id or not isinstance(connection_id, str):
        raise ValueError("Connection ID must be a non-empty string")

    if not keys or not isinstance(keys, list) or len(keys) == 0:
        raise ValueError("No API keys available")

    # If there's only one key, return it directly
    if len(keys) == 1:
        return keys[0]

    # Default options
    strategy = options.get("strategy", KeySelectionStrategy.RANDOM)
    enable_cache = options.get("enable_cache", True)
    cache_ttl = options.get("cache_ttl", 5 * 60)  # 5 minutes
    validate_key = options.get("validate_key")
    weights = options.get("weights", {})

    # Check cache first if enabled
    now = time.time()
    if (
        enable_cache
        and connection_id in _api_key_cache
        and now - _api_key_cache[connection_id]["timestamp"] < cache_ttl
    ):
        logger.debug(f"Using cached API key selection for connection: {connection_id}")
        return _select_key_from_cache(
            connection_id, keys, strategy, weights, validate_key
        )

    # Update cache
    _api_key_cache[connection_id] = {
        "keys": keys,
        "timestamp": now,
        "last_used_index": _api_key_cache.get(connection_id, {}).get("last_used_index"),
        "last_used": _api_key_cache.get(connection_id, {}).get("last_used", {}),
    }

    return _select_key_from_cache(connection_id, keys, strategy, weights, validate_key)


def _select_key_from_cache(
    connection_id: str,
    keys: List[str],
    strategy: str,
    weights: Dict[str, float],
    validate_key: Optional[Callable[[str], bool]] = None,
) -> str:
    """
    Helper function to select a key from the cache based on the specified strategy

    Args:
        connection_id: Unique identifier for the connection
        keys: List of API keys
        strategy: Selection strategy to use
        weights: Key weights for weighted distribution
        validate_key: Optional validation function

    Returns:
        The selected API key

    Raises:
        ValueError: If no valid API keys are available
    """
    cache = _api_key_cache[connection_id]
    selected_key = None

    if strategy == KeySelectionStrategy.ROUND_ROBIN:
        # Initialize or increment the last used index
        if "last_used_index" not in cache or cache["last_used_index"] is None:
            cache["last_used_index"] = 0
        else:
            cache["last_used_index"] = (cache["last_used_index"] + 1) % len(keys)

        selected_key = keys[cache["last_used_index"]]

        # Log the selected key (masked) at debug level
        logger.debug(
            f"Selected API key (Round-robin): {mask_api_key(selected_key)} for connection: {connection_id}"
        )

    elif strategy == KeySelectionStrategy.LEAST_RECENTLY_USED:
        # Initialize lastUsed if needed
        if "last_used" not in cache or not cache["last_used"]:
            cache["last_used"] = {key: 0.0 for key in keys}

        # Find the least recently used key
        selected_key = min(keys, key=lambda k: cache["last_used"].get(k, 0))

        # Update the last used timestamp
        cache["last_used"][selected_key] = time.time()
        # Log the selected key (masked) at debug level
        logger.debug(
            f"Selected API key (LRU): {mask_api_key(selected_key)} for connection: {connection_id}"
        )

    elif strategy == KeySelectionStrategy.WEIGHTED:
        # Check if weights are provided
        has_weights = bool(weights)

        if has_weights:
            # Calculate total weight
            total_weight = 0.0
            key_weights = []

            for key in keys:
                weight = float(weights.get(key, 1))
                key_weights.append(weight)
                total_weight += weight

            # Select a random point in the total weight
            random_point = random.random() * total_weight
            weight_sum = 0.0
            key_selected = False

            # Find the key at the random point
            for i, key in enumerate(keys):
                weight_sum += key_weights[i]
                if random_point <= weight_sum:
                    selected_key = key
                    key_selected = True

                    # Log the selected key (masked) at debug level
                    logger.debug(
                        f"Selected API key (Weighted): {mask_api_key(selected_key)} for connection: {connection_id}"
                    )
                    break

            # Fallback to first key if something went wrong
            if not key_selected:
                selected_key = keys[0]

                # Log the selected key (masked) at debug level
                logger.debug(
                    f"Selected API key (Weighted fallback): {mask_api_key(selected_key)} for connection: {connection_id}"
                )
        else:
            # If no weights provided, fall back to random selection
            random_index = random.randint(0, len(keys) - 1)
            selected_key = keys[random_index]

            # Log the selected key (masked) at debug level
            logger.debug(
                f"Selected API key (Random fallback): {mask_api_key(selected_key)} for connection: {connection_id}"
            )

    else:  # Default to RANDOM
        # Select a random key
        random_index = random.randint(0, len(keys) - 1)
        selected_key = keys[random_index]

        # Log the selected key (masked) at debug level
        logger.debug(
            f"Selected API key (Random): {mask_api_key(selected_key)} for connection: {connection_id}"
        )

    # Validate the selected key if a validation function is provided
    if selected_key and validate_key and not validate_key(selected_key):
        # Try to find a valid key
        valid_key = next((key for key in keys if validate_key(key)), None)
        if valid_key:
            # Log the selected key (masked) at debug level
            logger.debug(
                f"Selected API key (Validation fallback): {mask_api_key(valid_key)} for connection: {connection_id}"
            )
            return valid_key
        raise ValueError(f"No valid API keys available for connection: {connection_id}")

    return selected_key or keys[0]


def clear_api_key_cache(connection_id: Optional[str] = None) -> None:
    """
    Clear the API key cache for a specific connection or all connections

    Args:
        connection_id: Optional connection ID to clear cache for. If not provided, clears all caches.
    """
    global _api_key_cache
    if connection_id:
        if connection_id in _api_key_cache:
            del _api_key_cache[connection_id]
            logger.debug(f"Cleared API key cache for connection: {connection_id}")
    else:
        _api_key_cache = {}
        logger.debug("Cleared all API key caches")
