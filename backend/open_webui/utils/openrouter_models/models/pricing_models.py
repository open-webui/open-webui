"""Pricing domain models and data transfer objects"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


class ModelCategory(Enum):
    """Model pricing categories"""
    BUDGET = "Budget"
    STANDARD = "Standard"
    FAST = "Fast"
    PREMIUM = "Premium"
    REASONING = "Reasoning"


@dataclass
class ModelPricing:
    """Domain model for model pricing information"""
    id: str
    name: str
    provider: str
    price_per_million_input: float
    price_per_million_output: float
    context_length: int
    category: ModelCategory
    description: str = ""
    created: int = 0
    architecture: Dict[str, Any] = None
    top_provider: Dict[str, Any] = None
    per_request_limits: Optional[Dict[str, Any]] = None
    supported_parameters: List[str] = None
    
    def __post_init__(self):
        """Initialize defaults for mutable fields"""
        if self.architecture is None:
            self.architecture = {}
        if self.supported_parameters is None:
            self.supported_parameters = []
    
    @property
    def average_price(self) -> float:
        """Calculate average price for categorization"""
        return (self.price_per_million_input + self.price_per_million_output) / 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "price_per_million_input": self.price_per_million_input,
            "price_per_million_output": self.price_per_million_output,
            "context_length": self.context_length,
            "category": self.category.value,
            "description": self.description,
            "created": self.created,
            "architecture": self.architecture,
            "top_provider": self.top_provider,
            "per_request_limits": self.per_request_limits,
            "supported_parameters": self.supported_parameters
        }


@dataclass
class PricingResponse:
    """Response model for pricing API"""
    success: bool
    models: List[ModelPricing]
    last_updated: str
    source: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "success": self.success,
            "models": [model.to_dict() for model in self.models],
            "last_updated": self.last_updated,
            "source": self.source,
            "error": self.error
        }