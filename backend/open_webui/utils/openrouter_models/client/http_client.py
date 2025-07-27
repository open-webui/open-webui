"""HTTP client for OpenRouter API with connection pooling and retry logic"""

import httpx
import logging
from typing import Dict, Any, Optional
from .retry_policy import ExponentialBackoff, CircuitBreaker, RetryPolicy

log = logging.getLogger(__name__)


class OpenRouterHTTPClient:
    """HTTP client with connection pooling, retry, and circuit breaker"""
    
    def __init__(self, base_url: str = "https://openrouter.ai/api/v1"):
        self.base_url = base_url
        self.retry_policy = RetryPolicy()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        
        # Configure connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, pool=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            headers={
                "User-Agent": "mAI/1.0 (OpenWebUI Fork)",
                "Accept-Encoding": "gzip, deflate",  # Enable compression
            }
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close client"""
        await self.close()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    @ExponentialBackoff()
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request with retry logic
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: On HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        
        async def _make_request():
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        
        try:
            return await self.circuit_breaker.call(_make_request)
        except Exception as e:
            log.error(f"HTTP GET failed for {url}: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if the API is accessible
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Use a lightweight endpoint for health check
            await self.get("/models", params={"limit": 1})
            return True
        except Exception as e:
            log.warning(f"Health check failed: {e}")
            return False