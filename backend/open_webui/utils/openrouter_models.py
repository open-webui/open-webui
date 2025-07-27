"""
OpenRouter Models API Integration - Refactored with Repository Pattern

This module provides dynamic model pricing from OpenRouter API with:
- Smart multi-tier caching (in-memory + Redis)
- Retry mechanisms with exponential backoff
- Background refresh to prevent cache misses
- Circuit breaker for API health protection

This is the main entry point that maintains backward compatibility.
"""

from .openrouter_models.services.pricing_calculator import PricingCalculatorService
from .openrouter_models.services.cache_manager import CacheManager
from .openrouter_models.repository.cached_repo import CachedOpenRouterRepository
from .openrouter_models.repository.openrouter_repo import OpenRouterRepository

# Initialize services
_repository = OpenRouterRepository()
_cached_repository = CachedOpenRouterRepository(_repository)
_pricing_service = PricingCalculatorService(_cached_repository)

# Public API - maintain backward compatibility
async def get_dynamic_model_pricing(force_refresh: bool = False):
    """
    Get model pricing information from OpenRouter
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dictionary containing model pricing information
    """
    return await _pricing_service.get_model_pricing(force_refresh=force_refresh)

# For backward compatibility with scripts that use the old class
OpenRouterModelsAPI = OpenRouterRepository

# Create global instance for backward compatibility
openrouter_models_api = OpenRouterRepository()

# Export main classes for direct usage if needed
__all__ = [
    'get_dynamic_model_pricing',
    'PricingCalculatorService',
    'CacheManager',
    'CachedOpenRouterRepository',
    'OpenRouterRepository',
    'OpenRouterModelsAPI',
    'openrouter_models_api'
]