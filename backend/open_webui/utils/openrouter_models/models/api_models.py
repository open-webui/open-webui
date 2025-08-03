"""API response models for OpenRouter integration"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class OpenRouterModel:
    """Model data from OpenRouter API"""
    id: str
    name: str
    pricing: Dict[str, str]  # {"prompt": "0.000001", "completion": "0.000002"}
    context_length: int
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
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'OpenRouterModel':
        """Create instance from API response data"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            pricing=data.get("pricing", {}),
            context_length=data.get("context_length", 0),
            description=data.get("description", ""),
            created=data.get("created", 0),
            architecture=data.get("architecture", {}),
            top_provider=data.get("top_provider", {}),
            per_request_limits=data.get("per_request_limits"),
            supported_parameters=data.get("supported_parameters", [])
        )


@dataclass
class OpenRouterResponse:
    """Response from OpenRouter API"""
    data: List[Dict[str, Any]]
    
    @property
    def models(self) -> List[OpenRouterModel]:
        """Convert raw data to model objects"""
        return [OpenRouterModel.from_api_response(model_data) for model_data in self.data]