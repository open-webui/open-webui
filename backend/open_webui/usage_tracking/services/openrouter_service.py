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
        """Fetch generation data from OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        url = "https://openrouter.ai/api/v1/generations"
        params = {
            "limit": limit,
            "offset": offset
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")