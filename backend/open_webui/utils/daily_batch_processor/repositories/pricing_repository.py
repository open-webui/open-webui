"""
Repository for pricing data operations
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..utils.async_db import AsyncDatabase

log = logging.getLogger(__name__)


class PricingRepository:
    """Repository for model pricing data"""
    
    def __init__(self, db: AsyncDatabase):
        self.db = db
        self._pricing_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        
    async def get_cached_pricing(self) -> Optional[Dict[str, Any]]:
        """Get cached pricing data if available and fresh"""
        if self._pricing_cache and self._cache_timestamp:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 3600:  # 1 hour cache
                return self._pricing_cache
        return None
        
    async def update_pricing_cache(self, pricing_data: Dict[str, Any]) -> None:
        """Update the pricing cache"""
        self._pricing_cache = pricing_data
        self._cache_timestamp = datetime.now()
        
    async def get_model_price(self, model_id: str) -> Optional[float]:
        """Get price for a specific model from cache"""
        if self._pricing_cache and "models" in self._pricing_cache:
            for model in self._pricing_cache["models"]:
                if model.get("id") == model_id:
                    return model.get("price_per_million", 0.0)
        return None
        
    async def store_pricing_snapshot(self, pricing_data: Dict[str, Any]) -> None:
        """Store a snapshot of pricing data for audit purposes"""
        # This could be extended to store in a pricing_snapshots table
        # For now, we just update the cache
        await self.update_pricing_cache(pricing_data)