"""
Configuration for NBP Service
"""
import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Service configuration
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("PORT", "8001"))
    
    # NBP API configuration
    nbp_api_url: str = os.getenv("NBP_API_URL", "https://api.nbp.pl/api/exchangerates/rates/a/usd/")
    mock_mode: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
    
    # Cache configuration
    cache_ttl: int = int(os.getenv("CACHE_TTL", "7200"))  # 2 hours
    fetch_interval: int = int(os.getenv("FETCH_INTERVAL", "3600"))  # 1 hour
    
    # Redis configuration (for production)
    redis_url: Optional[str] = os.getenv("REDIS_URL", None)
    
    # Performance settings
    request_timeout: int = 10  # seconds
    max_retries: int = 3
    
    # CORS settings
    cors_origins: list = ["*"]  # Configure appropriately for production
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()