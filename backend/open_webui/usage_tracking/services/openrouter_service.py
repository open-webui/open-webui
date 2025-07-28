"""
OpenRouter Service - External API integration
Handles all OpenRouter API communication
"""

from typing import Dict, Any
import requests
from fastapi import HTTPException


class OpenRouterService:
    """Service for OpenRouter API integration"""
    
    @staticmethod
    async def get_generations(api_key: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        DEPRECATED: OpenRouter bulk generation fetching is disabled
        
        The OpenRouter API does not provide a bulk generations endpoint (/api/v1/generations).
        This method was causing 404 errors and system confusion.
        
        Real-time usage tracking via webhooks is the primary method for usage data collection.
        """
        raise HTTPException(
            status_code=501, 
            detail={
                "error": "Bulk sync disabled",
                "message": "OpenRouter bulk generation fetching is no longer supported. The API endpoint /api/v1/generations does not exist and was causing system errors.",
                "alternative": "Real-time usage tracking via webhooks is the primary method for collecting usage data.",
                "status": "deprecated"
            }
        )