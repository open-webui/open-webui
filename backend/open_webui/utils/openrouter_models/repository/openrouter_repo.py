"""OpenRouter API repository implementation"""

import logging
from typing import List, Optional
from datetime import datetime

from ..models.pricing_models import ModelPricing, ModelCategory
from ..models.api_models import OpenRouterResponse, OpenRouterModel
from ..client.http_client import OpenRouterHTTPClient
from .interface import ModelPricingRepository, RepositoryError

log = logging.getLogger(__name__)


class OpenRouterRepository(ModelPricingRepository):
    """Repository for fetching model pricing from OpenRouter API"""
    
    def __init__(self):
        self.client = None
        self._fallback_models = self._get_hardcoded_models()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = OpenRouterHTTPClient()
    
    async def fetch_all_models(self) -> List[ModelPricing]:
        """
        Fetch all models from OpenRouter API
        
        Returns:
            List of ModelPricing objects
            
        Raises:
            RepositoryError: If API call fails
        """
        try:
            await self._ensure_client()
            response_data = await self.client.get("/models")
            response = OpenRouterResponse(data=response_data.get("data", []))
            
            models = []
            for api_model in response.models:
                try:
                    pricing_model = self._map_to_pricing_model(api_model)
                    models.append(pricing_model)
                except Exception as e:
                    log.warning(f"Failed to map model {api_model.id}: {e}")
                    continue
            
            # Sort by provider and name for consistent display
            models.sort(key=lambda x: (x.provider, x.name))
            
            log.info(f"Fetched {len(models)} models from OpenRouter API")
            return models
            
        except Exception as e:
            log.error(f"Failed to fetch models from OpenRouter: {e}")
            raise RepositoryError(f"API fetch failed: {str(e)}")
    
    async def fetch_model_by_id(self, model_id: str) -> Optional[ModelPricing]:
        """
        Fetch a specific model by ID
        
        Args:
            model_id: The model identifier
            
        Returns:
            ModelPricing object if found, None otherwise
        """
        try:
            models = await self.fetch_all_models()
            return next((m for m in models if m.id == model_id), None)
        except RepositoryError:
            # Check fallback models
            return next((m for m in self._fallback_models if m.id == model_id), None)
    
    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible"""
        await self._ensure_client()
        return await self.client.health_check()
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.close()
            self.client = None
    
    def _map_to_pricing_model(self, api_model: OpenRouterModel) -> ModelPricing:
        """
        Map OpenRouter API model to our domain model
        
        Args:
            api_model: Model from API response
            
        Returns:
            ModelPricing domain object
        """
        # Extract pricing (OpenRouter returns prices as strings in USD per token)
        prompt_price = float(api_model.pricing.get("prompt", "0"))
        completion_price = float(api_model.pricing.get("completion", "0"))
        
        # Convert to per million tokens
        price_per_million_input = prompt_price * 1_000_000
        price_per_million_output = completion_price * 1_000_000
        
        # Determine category
        category = self._determine_category(price_per_million_input, price_per_million_output)
        
        # Extract provider from model ID
        provider = api_model.id.split("/")[0].title() if "/" in api_model.id else "Unknown"
        
        return ModelPricing(
            id=api_model.id,
            name=api_model.name or api_model.id,
            provider=provider,
            price_per_million_input=price_per_million_input,
            price_per_million_output=price_per_million_output,
            context_length=api_model.context_length,
            category=category,
            description=api_model.description,
            created=api_model.created,
            architecture=api_model.architecture,
            top_provider=api_model.top_provider,
            per_request_limits=api_model.per_request_limits,
            supported_parameters=api_model.supported_parameters
        )
    
    def _determine_category(self, input_price: float, output_price: float) -> ModelCategory:
        """Determine model category based on pricing"""
        avg_price = (input_price + output_price) / 2
        
        if avg_price < 1.0:
            return ModelCategory.BUDGET
        elif avg_price < 5.0:
            return ModelCategory.STANDARD
        elif avg_price < 10.0:
            return ModelCategory.FAST
        elif avg_price < 50.0:
            return ModelCategory.PREMIUM
        else:
            return ModelCategory.REASONING
    
    def _get_hardcoded_models(self) -> List[ModelPricing]:
        """Get hardcoded fallback models"""
        # Same fallback data as original implementation
        return [
            ModelPricing(
                id="anthropic/claude-sonnet-4",
                name="Claude Sonnet 4",
                provider="Anthropic",
                price_per_million_input=8.00,
                price_per_million_output=24.00,
                context_length=1000000,
                category=ModelCategory.PREMIUM
            ),
            ModelPricing(
                id="google/gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                provider="Google",
                price_per_million_input=1.50,
                price_per_million_output=6.00,
                context_length=2000000,
                category=ModelCategory.FAST
            ),
            ModelPricing(
                id="google/gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                provider="Google",
                price_per_million_input=3.00,
                price_per_million_output=12.00,
                context_length=2000000,
                category=ModelCategory.PREMIUM
            ),
            ModelPricing(
                id="deepseek/deepseek-chat-v3-0324",
                name="DeepSeek Chat v3",
                provider="DeepSeek",
                price_per_million_input=0.14,
                price_per_million_output=0.28,
                context_length=128000,
                category=ModelCategory.BUDGET
            ),
            ModelPricing(
                id="anthropic/claude-3.7-sonnet",
                name="Claude 3.7 Sonnet",
                provider="Anthropic",
                price_per_million_input=6.00,
                price_per_million_output=18.00,
                context_length=200000,
                category=ModelCategory.PREMIUM
            ),
            ModelPricing(
                id="anthropic/claude-3.5-haiku",
                name="Claude 3.5 Haiku",
                provider="Anthropic",
                price_per_million_input=0.50,
                price_per_million_output=2.00,
                context_length=200000,
                category=ModelCategory.STANDARD
            ),
            ModelPricing(
                id="openai/gpt-4o",
                name="GPT-4 Omni",
                provider="OpenAI",
                price_per_million_input=10.00,
                price_per_million_output=30.00,
                context_length=128000,
                category=ModelCategory.PREMIUM
            ),
            ModelPricing(
                id="openai/gpt-4o-mini",
                name="GPT-4 Omni Mini",
                provider="OpenAI",
                price_per_million_input=0.15,
                price_per_million_output=0.60,
                context_length=128000,
                category=ModelCategory.BUDGET
            ),
            ModelPricing(
                id="openai/gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="OpenAI",
                price_per_million_input=3.00,
                price_per_million_output=12.00,
                context_length=16385,
                category=ModelCategory.STANDARD
            ),
            ModelPricing(
                id="google/gemini-flash-1.5-exp",
                name="Gemini Flash 1.5 Experimental",
                provider="Google",
                price_per_million_input=0.00,
                price_per_million_output=0.00,
                context_length=1000000,
                category=ModelCategory.BUDGET
            ),
            ModelPricing(
                id="openai/o1-preview",
                name="O1 Preview",
                provider="OpenAI",
                price_per_million_input=60.00,
                price_per_million_output=240.00,
                context_length=128000,
                category=ModelCategory.REASONING
            ),
            ModelPricing(
                id="openai/gpt-4",
                name="GPT-4",
                provider="OpenAI",
                price_per_million_input=5.00,
                price_per_million_output=15.00,
                context_length=128000,
                category=ModelCategory.STANDARD
            )
        ]