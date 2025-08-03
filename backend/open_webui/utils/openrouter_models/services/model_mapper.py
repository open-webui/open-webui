"""Model mapping service for data transformation"""

import logging
from typing import List, Dict, Any

from ..models.pricing_models import ModelPricing, ModelCategory

log = logging.getLogger(__name__)


class ModelMapperService:
    """Service for mapping and transforming model data"""
    
    @staticmethod
    def filter_mai_models(models: List[ModelPricing]) -> List[ModelPricing]:
        """
        Filter models to only include mAI-supported ones
        
        Args:
            models: List of all models
            
        Returns:
            Filtered list of mAI models
        """
        mai_model_ids = {
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash", 
            "google/gemini-2.5-pro",
            "deepseek/deepseek-chat-v3-0324",
            "anthropic/claude-3.7-sonnet",
            "google/gemini-2.5-flash-lite-preview-06-17",
            "openai/gpt-4.1",
            "x-ai/grok-4",
            "openai/gpt-4o-mini",
            "openai/o4-mini-high",
            "openai/o3",
            "openai/chatgpt-4o-latest",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4o",
            "openai/gpt-3.5-turbo",
            "google/gemini-flash-1.5-exp",
            "openai/o1-preview",
            "openai/gpt-4"
        }
        
        filtered = [model for model in models if model.id in mai_model_ids]
        log.debug(f"Filtered {len(models)} models to {len(filtered)} mAI-supported models")
        
        return filtered
    
    @staticmethod
    def group_by_provider(models: List[ModelPricing]) -> Dict[str, List[ModelPricing]]:
        """
        Group models by provider
        
        Args:
            models: List of models
            
        Returns:
            Dictionary with provider as key and list of models as value
        """
        grouped = {}
        for model in models:
            provider = model.provider
            if provider not in grouped:
                grouped[provider] = []
            grouped[provider].append(model)
        
        # Sort models within each provider by price
        for provider in grouped:
            grouped[provider].sort(key=lambda m: m.average_price)
        
        return grouped
    
    @staticmethod
    def group_by_category(models: List[ModelPricing]) -> Dict[str, List[ModelPricing]]:
        """
        Group models by category
        
        Args:
            models: List of models
            
        Returns:
            Dictionary with category as key and list of models as value
        """
        grouped = {}
        for model in models:
            category = model.category.value
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(model)
        
        # Sort models within each category by price
        for category in grouped:
            grouped[category].sort(key=lambda m: m.average_price)
        
        return grouped
    
    @staticmethod
    def create_price_comparison(models: List[ModelPricing]) -> List[Dict[str, Any]]:
        """
        Create price comparison data for frontend display
        
        Args:
            models: List of models
            
        Returns:
            List of comparison data
        """
        comparison = []
        
        for model in models:
            comparison.append({
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "category": model.category.value,
                "input_price": model.price_per_million_input,
                "output_price": model.price_per_million_output,
                "average_price": model.average_price,
                "context_length": model.context_length,
                "cost_per_1k_tokens": {
                    "input": model.price_per_million_input / 1000,
                    "output": model.price_per_million_output / 1000,
                    "average": model.average_price / 1000
                }
            })
        
        # Sort by average price
        comparison.sort(key=lambda x: x["average_price"])
        
        return comparison