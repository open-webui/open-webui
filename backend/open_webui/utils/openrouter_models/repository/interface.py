"""Repository interface for model pricing data access"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.pricing_models import ModelPricing


class ModelPricingRepository(ABC):
    """Abstract interface for model pricing data repository"""
    
    @abstractmethod
    async def fetch_all_models(self) -> List[ModelPricing]:
        """
        Fetch all available models with pricing
        
        Returns:
            List of ModelPricing objects
            
        Raises:
            RepositoryError: If fetch operation fails
        """
        pass
    
    @abstractmethod
    async def fetch_model_by_id(self, model_id: str) -> Optional[ModelPricing]:
        """
        Fetch a specific model by ID
        
        Args:
            model_id: The model identifier
            
        Returns:
            ModelPricing object if found, None otherwise
            
        Raises:
            RepositoryError: If fetch operation fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the repository is healthy and accessible
        
        Returns:
            True if healthy, False otherwise
        """
        pass


class RepositoryError(Exception):
    """Base exception for repository errors"""
    pass