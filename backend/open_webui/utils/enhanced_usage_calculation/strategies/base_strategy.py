"""
Base strategy interface for usage calculations
Defines the contract for all calculation strategies
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import date as DateType

from ..models.calculation_models import CalculationContext, CalculationResult
from ..models.result_models import ClientUsageStats


class BaseCalculationStrategy(ABC):
    """Abstract base class for all calculation strategies"""
    
    def __init__(self, cache_ttl: int = 300):
        """
        Initialize strategy with cache configuration
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self._cache = {}  # Simple in-memory cache, will be replaced with Redis
    
    @abstractmethod
    def calculate(self, context: CalculationContext) -> CalculationResult:
        """
        Perform the calculation based on the context
        
        Args:
            context: Calculation context with client info and parameters
            
        Returns:
            CalculationResult with the computed data
        """
        pass
    
    @abstractmethod
    def get_cache_key(self, context: CalculationContext) -> str:
        """
        Generate a unique cache key for this calculation
        
        Args:
            context: Calculation context
            
        Returns:
            Unique cache key string
        """
        pass
    
    def invalidate_cache(self, client_org_id: str) -> None:
        """
        Invalidate cache entries for a specific client
        
        Args:
            client_org_id: Client organization ID
        """
        keys_to_remove = [
            key for key in self._cache.keys() 
            if client_org_id in key
        ]
        for key in keys_to_remove:
            del self._cache[key]
    
    def _get_from_cache(self, key: str) -> Optional[CalculationResult]:
        """
        Retrieve result from cache if available and not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached result or None if not found/expired
        """
        # Simple implementation, will be enhanced with TTL checks
        return self._cache.get(key)
    
    def _store_in_cache(self, key: str, result: CalculationResult) -> None:
        """
        Store result in cache
        
        Args:
            key: Cache key
            result: Calculation result to cache
        """
        self._cache[key] = result