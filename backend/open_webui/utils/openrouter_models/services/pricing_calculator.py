"""Pricing calculation service with business logic"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.pricing_models import ModelPricing, PricingResponse
from ..repository.interface import ModelPricingRepository, RepositoryError
from ..utils.monitoring import TimedOperation

log = logging.getLogger(__name__)


class PricingCalculatorService:
    """Service for model pricing calculations and business logic"""
    
    def __init__(self, repository: ModelPricingRepository):
        self.repository = repository
        
    async def get_model_pricing(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get model pricing information
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing model pricing information
        """
        with TimedOperation("get_model_pricing"):
            try:
                if force_refresh and hasattr(self.repository, 'invalidate_cache'):
                    await self.repository.invalidate_cache()
                
                models = await self.repository.fetch_all_models()
                
                response = PricingResponse(
                    success=True,
                    models=models,
                    last_updated=datetime.now().isoformat(),
                    source="openrouter_api"
                )
                
                return response.to_dict()
                
            except RepositoryError as e:
                log.error(f"Failed to get model pricing: {e}")
                
                # Return fallback response
                return self._get_fallback_response(str(e))
    
    async def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific model pricing
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model pricing data or None
        """
        model = await self.repository.fetch_model_by_id(model_id)
        return model.to_dict() if model else None
    
    async def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        markup_rate: float = 1.3
    ) -> Dict[str, float]:
        """
        Calculate cost for token usage
        
        Args:
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            markup_rate: Markup rate to apply (default 1.3)
            
        Returns:
            Dictionary with cost breakdown
        """
        model = await self.repository.fetch_model_by_id(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")
        
        # Calculate raw costs
        input_cost = (input_tokens / 1_000_000) * model.price_per_million_input
        output_cost = (output_tokens / 1_000_000) * model.price_per_million_output
        raw_cost = input_cost + output_cost
        
        # Apply markup
        markup_cost = raw_cost * markup_rate
        
        return {
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "raw_cost": raw_cost,
            "markup_rate": markup_rate,
            "markup_cost": markup_cost,
            "price_per_million_input": model.price_per_million_input,
            "price_per_million_output": model.price_per_million_output
        }
    
    async def get_models_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get models filtered by category
        
        Args:
            category: Category name (Budget, Standard, Premium, etc.)
            
        Returns:
            List of models in the category
        """
        all_models = await self.repository.fetch_all_models()
        filtered = [
            model for model in all_models
            if model.category.value.lower() == category.lower()
        ]
        
        return [model.to_dict() for model in filtered]
    
    async def get_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get models filtered by provider
        
        Args:
            provider: Provider name (OpenAI, Anthropic, etc.)
            
        Returns:
            List of models from the provider
        """
        all_models = await self.repository.fetch_all_models()
        filtered = [
            model for model in all_models
            if model.provider.lower() == provider.lower()
        ]
        
        return [model.to_dict() for model in filtered]
    
    async def get_cheapest_models(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get cheapest models by average price
        
        Args:
            limit: Number of models to return
            
        Returns:
            List of cheapest models
        """
        all_models = await self.repository.fetch_all_models()
        sorted_models = sorted(all_models, key=lambda m: m.average_price)
        
        return [model.to_dict() for model in sorted_models[:limit]]
    
    def _get_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """Get fallback response when API fails"""
        # Get hardcoded models from repository if available
        fallback_models = []
        if hasattr(self.repository, '_get_hardcoded_models'):
            fallback_models = self.repository._get_hardcoded_models()
        
        response = PricingResponse(
            success=False,
            models=fallback_models,
            last_updated=datetime.now().isoformat(),
            source="hardcoded_fallback",
            error=error_message
        )
        
        return response.to_dict()