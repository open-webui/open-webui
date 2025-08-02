"""
NBP Service - Provides USD/PLN exchange rates for mAI
Supports both real NBP API and mock mode for development
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional

from .config import settings
from .services.nbp_client import NBPClient
from .services.cache_service import CacheService
from .services.redis_cache_service import RedisCacheService
from .services.scheduler import RateUpdateScheduler
from .models import ExchangeRateResponse, HealthResponse
from .monitoring import metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.env == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
if settings.redis_url and settings.env == "production":
    cache_service = RedisCacheService()
else:
    cache_service = CacheService()

nbp_client = NBPClient(
    mock_mode=settings.mock_mode,
    cache_service=cache_service
)

# Initialize scheduler
scheduler = RateUpdateScheduler(nbp_client, cache_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info(f"Starting NBP Service in {'MOCK' if nbp_client.mock_mode else 'LIVE'} mode")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Cache TTL: {settings.cache_ttl} seconds")
    
    # Pre-fetch current rate on startup (optional)
    if not settings.mock_mode:
        try:
            current_rate = await nbp_client.get_rate()
            logger.info(f"Current USD/PLN rate: {current_rate.rate}")
        except Exception as e:
            logger.error(f"Failed to fetch initial rate: {e}")
    
    # Start background scheduler
    await scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down NBP Service")
    
    # Stop scheduler
    await scheduler.stop()
    
    # Close connections
    if nbp_client.session:
        await nbp_client.close()
    if hasattr(cache_service, 'close'):
        await cache_service.close()


# Create FastAPI app
app = FastAPI(
    title="NBP Exchange Rate Service",
    description="Provides USD/PLN exchange rates for mAI usage tracking",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        mode="mock" if nbp_client.mock_mode else "live",
        timestamp=datetime.utcnow()
    )


@app.get("/api/usd-pln-rate", response_model=ExchangeRateResponse)
async def get_usd_pln_rate(date: Optional[str] = None):
    """
    Get USD/PLN exchange rate
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, returns current rate.
    
    Returns:
        Exchange rate information including rate, date, and source
    """
    metrics.record_request()
    
    try:
        # Check cache first
        cache_key = f"usd_pln_{date or 'current'}"
        cached = cache_service.get(cache_key)
        
        if cached:
            metrics.record_cache_hit()
            return cached
        else:
            metrics.record_cache_miss()
        
        # Fetch from NBP
        rate_data = await nbp_client.get_rate(date)
        metrics.record_api_call(success=True)
        
        return rate_data
    except Exception as e:
        metrics.record_error(str(e))
        metrics.record_api_call(success=False)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usd-pln-rate/range")
async def get_usd_pln_rate_range(start_date: str, end_date: str):
    """
    Get USD/PLN exchange rates for a date range
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of exchange rates for the specified period
    """
    try:
        rates = await nbp_client.get_rates_range(start_date, end_date)
        return {"rates": rates, "count": len(rates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the exchange rate cache (admin endpoint)"""
    if hasattr(cache_service, 'clear'):
        cache_service.clear()
    else:
        await cache_service.clear()
    return {"message": "Cache cleared successfully"}


@app.get("/metrics")
async def get_metrics():
    """Get service metrics and health information"""
    return metrics.get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)