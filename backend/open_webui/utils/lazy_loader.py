"""
Lazy Loader Module - Deferred loading of heavy modules to optimize startup time and memory.

This module provides lazy loading utilities for resource-intensive components like
SentenceTransformer and Whisper models. Models are loaded only when first accessed,
reducing initial memory footprint and startup time.

Usage:
    from open_webui.utils.lazy_loader import get_sentence_transformer
    SentenceTransformer = get_sentence_transformer()
    model = SentenceTransformer("model-name")
"""

import importlib
import logging
import threading
from functools import lru_cache
from typing import Any, TypeVar

log = logging.getLogger(__name__)
T = TypeVar("T")


class LazyModule:
    """
    Lazy loading wrapper for heavy modules.
    The module is imported only when first accessed.
    """

    def __init__(self, module_name: str):
        self._module_name = module_name
        self._module = None

    def _load(self):
        if self._module is None:
            log.debug(f"Lazy loading module: {self._module_name}")
            self._module = importlib.import_module(self._module_name)
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)


class LazyStateProxy:
    """
    Lazy proxy for app.state-backed objects (e.g., embedding/reranker models).
    Loads the object on first attribute access and caches it on app.state.
    """

    def __init__(self, state, attr: str, loader):
        self._state = state
        self._attr = attr
        self._loader = loader
        self._lock = threading.Lock()

    def _get(self):
        obj = getattr(self._state, self._attr, None)
        if obj is None:
            with self._lock:
                obj = getattr(self._state, self._attr, None)
                if obj is None:
                    obj = self._loader()
                    setattr(self._state, self._attr, obj)
        return obj

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


@lru_cache(maxsize=1)
def get_sentence_transformer():
    """
    Get SentenceTransformer class with lazy loading and LRU cache.
    The class is loaded only once on first call.
    
    Returns:
        SentenceTransformer class from sentence_transformers package
    """
    log.info("Loading SentenceTransformer (first use)...")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer


@lru_cache(maxsize=1)
def get_cross_encoder():
    """
    Get CrossEncoder class with lazy loading and LRU cache.
    
    Returns:
        CrossEncoder class from sentence_transformers package
    """
    log.info("Loading CrossEncoder (first use)...")
    import sentence_transformers
    return sentence_transformers.CrossEncoder


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Get WhisperModel class with lazy loading and LRU cache.
    
    Returns:
        WhisperModel class from faster_whisper package
    """
    log.info("Loading WhisperModel (first use)...")
    from faster_whisper import WhisperModel
    return WhisperModel


def clear_lazy_cache():
    """
    Clear all cached lazy-loaded modules to free memory.
    Call this when you want to unload models.
    """
    get_sentence_transformer.cache_clear()
    get_cross_encoder.cache_clear()
    get_whisper_model.cache_clear()
    log.info("Lazy loader cache cleared")
