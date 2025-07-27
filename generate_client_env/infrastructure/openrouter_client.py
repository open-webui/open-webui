"""
OpenRouter API client for infrastructure layer.

Handles all external API communication with OpenRouter services.
"""

import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    import requests
except ImportError:
    requests = None


@dataclass
class ApiResponse:
    """Represents an API response with metadata."""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class OpenRouterApiError(Exception):
    """Raised when OpenRouter API operations fail."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OpenRouterClient:
    """Client for OpenRouter Provisioning API operations."""
    
    def __init__(self, base_url: str = "https://openrouter.ai/api/v1", timeout: int = 30):
        if requests is None:
            raise ImportError(
                "requests library is required. Install with: pip install requests"
            )
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
    def validate_provisioning_key(self, provisioning_key: str) -> ApiResponse:
        """
        Validate provisioning key by testing API connectivity.
        
        Args:
            provisioning_key: OpenRouter provisioning API key
            
        Returns:
            ApiResponse with validation result
        """
        try:
            headers = self._build_headers(provisioning_key)
            
            response = requests.get(
                f"{self.base_url}/keys",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return ApiResponse(
                    success=True,
                    status_code=200,
                    data={"message": "Provisioning key validated successfully"}
                )
            elif response.status_code == 401:
                return ApiResponse(
                    success=False,
                    status_code=401,
                    error_message="Invalid provisioning key"
                )
            else:
                return ApiResponse(
                    success=False,
                    status_code=response.status_code,
                    error_message=f"Unexpected response: {response.text}"
                )
                
        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                status_code=None,
                error_message=f"Network error: {str(e)}"
            )
    
    def create_api_key(
        self, 
        provisioning_key: str, 
        key_data: Dict[str, Any]
    ) -> ApiResponse:
        """
        Create a new API key using OpenRouter Provisioning API.
        
        Args:
            provisioning_key: OpenRouter provisioning API key
            key_data: API key creation payload
            
        Returns:
            ApiResponse with created key data or error
        """
        try:
            headers = self._build_headers(provisioning_key)
            
            response = requests.post(
                f"{self.base_url}/keys",
                headers=headers,
                json=key_data,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Extract API key from various possible response formats
                api_key, key_hash = self._extract_key_from_response(result)
                
                if api_key:
                    return ApiResponse(
                        success=True,
                        status_code=response.status_code,
                        data={
                            "api_key": api_key,
                            "key_hash": key_hash,
                            "raw_response": result
                        }
                    )
                else:
                    return ApiResponse(
                        success=False,
                        status_code=response.status_code,
                        error_message="No API key found in response"
                    )
            else:
                return ApiResponse(
                    success=False,
                    status_code=response.status_code,
                    error_message=f"Failed to create API key: {response.text}"
                )
                
        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                status_code=None,
                error_message=f"Network error: {str(e)}"
            )
        except Exception as e:
            return ApiResponse(
                success=False,
                status_code=None,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def test_api_key(
        self, 
        api_key: str, 
        organization_name: str
    ) -> ApiResponse:
        """
        Test the generated API key and capture external_user.
        
        Args:
            api_key: Generated OpenRouter API key
            organization_name: Organization name for headers
            
        Returns:
            ApiResponse with test result and external_user if available
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://mai.example.com",
                "X-Title": f"mAI Client - {organization_name}"
            }
            
            test_payload = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello! This is a test message to initialize external_user mapping."
                    }
                ],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                external_user = result.get("external_user")
                
                return ApiResponse(
                    success=True,
                    status_code=200,
                    data={
                        "external_user": external_user,
                        "test_successful": True
                    }
                )
            else:
                return ApiResponse(
                    success=False,
                    status_code=response.status_code,
                    error_message=f"Test request failed: {response.text}",
                    data={"test_successful": False}
                )
                
        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                status_code=None,
                error_message=f"Network error during test: {str(e)}",
                data={"test_successful": False}
            )
        except Exception as e:
            return ApiResponse(
                success=False,
                status_code=None,
                error_message=f"Unexpected error during test: {str(e)}",
                data={"test_successful": False}
            )
    
    def _build_headers(self, provisioning_key: str) -> Dict[str, str]:
        """Build standard headers for OpenRouter API requests."""
        return {
            "Authorization": f"Bearer {provisioning_key}",
            "Content-Type": "application/json"
        }
    
    def _extract_key_from_response(self, response_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract API key and hash from OpenRouter response.
        
        Args:
            response_data: Raw API response data
            
        Returns:
            Tuple of (api_key, key_hash) or (None, None) if not found
        """
        # Try different response structures
        if "key" in response_data:
            api_key = response_data["key"]
            key_hash = response_data.get("data", {}).get("hash")
            return api_key, key_hash
        
        if "data" in response_data and isinstance(response_data["data"], dict):
            data = response_data["data"]
            if "key" in data:
                api_key = data["key"]
                key_hash = data.get("hash")
                return api_key, key_hash
        
        return None, None