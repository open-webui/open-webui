"""
Model pricing endpoint for usage tracking
Fetches dynamic pricing from OpenRouter API
"""

import logging
from fastapi import APIRouter, HTTPException
from open_webui.env import SRC_LOG_LEVELS
from open_webui.constants import MAI_BUSINESS_MODEL_IDS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/model-pricing")
async def get_mai_model_pricing(force_refresh: bool = False):
    """
    Get mAI model pricing information - dynamically fetched from OpenRouter API
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dictionary containing model pricing information
    """
    try:
        from open_webui.utils.openrouter_models import get_dynamic_model_pricing
        
        # Fetch dynamic pricing from OpenRouter API
        pricing_data = await get_dynamic_model_pricing(force_refresh=force_refresh)
        
        # Filter to only include models we actively use in mAI
        mai_model_ids = MAI_BUSINESS_MODEL_IDS
        
        # Filter models to only include our supported ones
        filtered_models = [
            model for model in pricing_data.get("models", [])
            if model["id"] in MAI_BUSINESS_MODEL_IDS
        ]
        
        # If no models found or API failed, use hardcoded fallback
        if not filtered_models and not pricing_data.get("success", False):
            # Return hardcoded models as fallback
            return {
                "success": False,
                "models": [
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
                        "id": "google/gemini-2.5-flash-lite-preview-06-17",
                        "name": "Gemini 2.5 Flash Lite",
                        "provider": "Google",
                        "price_per_million_input": 0.50,
                        "price_per_million_output": 2.00,
                        "context_length": 1000000,
                        "category": "Budget"
                    },
                    {
                        "id": "openai/gpt-4.1",
                        "name": "GPT-4.1",
                        "provider": "OpenAI",
                        "price_per_million_input": 10.00,
                        "price_per_million_output": 30.00,
                        "context_length": 128000,
                        "category": "Premium"
                    },
                    {
                        "id": "x-ai/grok-4",
                        "name": "Grok 4",
                        "provider": "xAI",
                        "price_per_million_input": 8.00,
                        "price_per_million_output": 24.00,
                        "context_length": 131072,
                        "category": "Premium"
                    },
                    {
                        "id": "openai/gpt-4o-mini",
                        "name": "GPT-4o Mini",
                        "provider": "OpenAI",
                        "price_per_million_input": 0.15,
                        "price_per_million_output": 0.60,
                        "context_length": 128000,
                        "category": "Budget"
                    },
                    {
                        "id": "openai/o4-mini-high",
                        "name": "O4 Mini High",
                        "provider": "OpenAI",
                        "price_per_million_input": 3.00,
                        "price_per_million_output": 12.00,
                        "context_length": 128000,
                        "category": "Standard"
                    },
                    {
                        "id": "openai/o3",
                        "name": "O3",
                        "provider": "OpenAI",
                        "price_per_million_input": 60.00,
                        "price_per_million_output": 240.00,
                        "context_length": 200000,
                        "category": "Reasoning"
                    },
                    {
                        "id": "openai/chatgpt-4o-latest",
                        "name": "ChatGPT-4o Latest",
                        "provider": "OpenAI",
                        "price_per_million_input": 5.00,
                        "price_per_million_output": 15.00,
                        "context_length": 128000,
                        "category": "Standard"
                    }
                ],
                "last_updated": pricing_data.get("last_updated"),
                "source": "hardcoded_fallback",
                "error": pricing_data.get("error", "Failed to fetch from OpenRouter API")
            }
        
        return {
            "success": pricing_data.get("success", False),
            "models": filtered_models,
            "last_updated": pricing_data.get("last_updated"),
            "source": pricing_data.get("source", "unknown")
        }
    except Exception as e:
        log.error(f"Failed to get model pricing: {e}")
        return {
            "success": False,
            "error": str(e),
            "models": [],
            "source": "error"
        }