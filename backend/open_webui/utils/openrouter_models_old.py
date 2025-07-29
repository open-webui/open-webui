"""
OpenRouter Models API Integration
Fetches current model pricing and information from OpenRouter API
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from cachetools import TTLCache

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class OpenRouterModelsAPI:
    """Handles fetching and caching model information from OpenRouter"""
    
    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/models"
        # Cache for 24 hours - prices update daily at 13:00 CET
        self.cache = TTLCache(maxsize=1, ttl=86400)
        self.cache_key = "openrouter_models"
        
    async def fetch_models(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch model information from OpenRouter API
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing model information with pricing
        """
        # Check cache first unless force refresh
        if not force_refresh and self.cache_key in self.cache:
            log.debug("Returning cached OpenRouter models data")
            return self.cache[self.cache_key]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url,
                    timeout=30.0,
                    headers={
                        "User-Agent": "mAI/1.0 (OpenWebUI Fork)"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Process and structure the data
                processed_data = self._process_models_data(data)
                
                # Cache the processed data
                self.cache[self.cache_key] = processed_data
                
                log.info(f"✅ Fetched {len(processed_data['models'])} models from OpenRouter API")
                
                return processed_data
                
        except httpx.TimeoutException:
            log.error("⏱️ Timeout fetching OpenRouter models")
            return self._get_fallback_data()
        except httpx.HTTPStatusError as e:
            log.error(f"❌ HTTP error fetching OpenRouter models: {e}")
            return self._get_fallback_data()
        except Exception as e:
            log.error(f"❌ Unexpected error fetching OpenRouter models: {e}")
            return self._get_fallback_data()
    
    def _process_models_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw OpenRouter API response into our format
        
        Args:
            raw_data: Raw response from OpenRouter API
            
        Returns:
            Processed data structure for our usage
        """
        models = []
        
        for model_data in raw_data.get("data", []):
            # Extract pricing information
            pricing = model_data.get("pricing", {})
            
            # Convert from per-token to per-million-token pricing
            # OpenRouter returns prices as strings in USD per token
            prompt_price = float(pricing.get("prompt", "0"))
            completion_price = float(pricing.get("completion", "0"))
            
            # Convert to per million tokens
            price_per_million_input = prompt_price * 1_000_000
            price_per_million_output = completion_price * 1_000_000
            
            # Determine category based on pricing
            category = self._determine_category(price_per_million_input, price_per_million_output)
            
            # Extract provider from model ID
            model_id = model_data.get("id", "")
            provider = model_id.split("/")[0].title() if "/" in model_id else "Unknown"
            
            models.append({
                "id": model_id,
                "name": model_data.get("name", model_id),
                "provider": provider,
                "price_per_million_input": price_per_million_input,
                "price_per_million_output": price_per_million_output,
                "context_length": model_data.get("context_length", 0),
                "category": category,
                "description": model_data.get("description", ""),
                "created": model_data.get("created", 0),
                "architecture": model_data.get("architecture", {}),
                "top_provider": model_data.get("top_provider", {}),
                "per_request_limits": model_data.get("per_request_limits"),
                "supported_parameters": model_data.get("supported_parameters", [])
            })
        
        # Sort by provider and name for consistent display
        models.sort(key=lambda x: (x["provider"], x["name"]))
        
        return {
            "success": True,
            "models": models,
            "last_updated": datetime.now().isoformat(),
            "source": "openrouter_api"
        }
    
    def _determine_category(self, input_price: float, output_price: float) -> str:
        """
        Determine model category based on pricing
        
        Args:
            input_price: Price per million input tokens
            output_price: Price per million output tokens
            
        Returns:
            Category string: Budget, Standard, Premium, Fast, or Reasoning
        """
        avg_price = (input_price + output_price) / 2
        
        if avg_price < 1.0:
            return "Budget"
        elif avg_price < 5.0:
            return "Standard"
        elif avg_price < 10.0:
            return "Fast"
        elif avg_price < 50.0:
            return "Premium"
        else:
            return "Reasoning"
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """
        Return fallback data when API is unavailable
        
        Returns:
            Fallback model data structure
        """
        # Check if we have cached data
        if self.cache_key in self.cache:
            log.warning("⚠️ Using cached data due to API error")
            cached_data = self.cache[self.cache_key]
            cached_data["source"] = "cache_fallback"
            return cached_data
        
        # Return hardcoded fallback as last resort
        log.warning("⚠️ Using hardcoded fallback data")
        return {
            "success": False,
            "models": self._get_hardcoded_models(),
            "last_updated": datetime.now().isoformat(),
            "source": "hardcoded_fallback",
            "error": "Failed to fetch from OpenRouter API"
        }
    
    def _get_hardcoded_models(self) -> List[Dict[str, Any]]:
        """
        Hardcoded model list as ultimate fallback
        
        Returns:
            List of model dictionaries
        """
        return [
            {
                "id": "anthropic/claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "provider": "Anthropic",
                "price_per_million_input": 8.00,
                "price_per_million_output": 24.00,
                "context_length": 1000000,
                "category": "Premium"
            },
            {
                "id": "google/gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "Google",
                "price_per_million_input": 1.50,
                "price_per_million_output": 6.00,
                "context_length": 2000000,
                "category": "Fast"
            },
            {
                "id": "google/gemini-2.5-pro",
                "name": "Gemini 2.5 Pro",
                "provider": "Google",
                "price_per_million_input": 3.00,
                "price_per_million_output": 12.00,
                "context_length": 2000000,
                "category": "Premium"
            },
            {
                "id": "deepseek/deepseek-chat-v3-0324",
                "name": "DeepSeek Chat v3",
                "provider": "DeepSeek",
                "price_per_million_input": 0.14,
                "price_per_million_output": 0.28,
                "context_length": 128000,
                "category": "Budget"
            },
            {
                "id": "anthropic/claude-3.7-sonnet",
                "name": "Claude 3.7 Sonnet",
                "provider": "Anthropic",
                "price_per_million_input": 6.00,
                "price_per_million_output": 18.00,
                "context_length": 200000,
                "category": "Premium"
            },
            {
                "id": "anthropic/claude-3.5-haiku",
                "name": "Claude 3.5 Haiku",
                "provider": "Anthropic",
                "price_per_million_input": 0.50,
                "price_per_million_output": 2.00,
                "context_length": 200000,
                "category": "Standard"
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4 Omni",
                "provider": "OpenAI",
                "price_per_million_input": 10.00,
                "price_per_million_output": 30.00,
                "context_length": 128000,
                "category": "Premium"
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4 Omni Mini",
                "provider": "OpenAI",
                "price_per_million_input": 0.15,
                "price_per_million_output": 0.60,
                "context_length": 128000,
                "category": "Budget"
            },
            {
                "id": "openai/gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "provider": "OpenAI",
                "price_per_million_input": 3.00,
                "price_per_million_output": 12.00,
                "context_length": 16385,
                "category": "Standard"
            },
            {
                "id": "google/gemini-flash-1.5-exp",
                "name": "Gemini Flash 1.5 Experimental",
                "provider": "Google",
                "price_per_million_input": 0.00,
                "price_per_million_output": 0.00,
                "context_length": 1000000,
                "category": "Budget"
            },
            {
                "id": "openai/o1-preview",
                "name": "O1 Preview",
                "provider": "OpenAI",
                "price_per_million_input": 60.00,
                "price_per_million_output": 240.00,
                "context_length": 128000,
                "category": "Reasoning"
            },
            {
                "id": "openai/gpt-4",
                "name": "GPT-4",
                "provider": "OpenAI",
                "price_per_million_input": 5.00,
                "price_per_million_output": 15.00,
                "context_length": 128000,
                "category": "Standard"
            }
        ]


# Global instance
openrouter_models_api = OpenRouterModelsAPI()


async def get_dynamic_model_pricing(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get model pricing information from OpenRouter
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dictionary containing model pricing information
    """
    return await openrouter_models_api.fetch_models(force_refresh)