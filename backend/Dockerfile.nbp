# NBP Currency Service Dockerfile
# Lightweight FastAPI service for USD/PLN exchange rates
FROM python:3.12-slim

WORKDIR /app

# Install required packages for NBP service
RUN pip install fastapi uvicorn httpx python-multipart

# Create NBP service
COPY <<EOF /app/nbp_service.py
from fastapi import FastAPI, HTTPException
import httpx
import asyncio
from datetime import datetime, timedelta
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="mAI NBP Currency Service", version="1.0.0")

# In-memory cache
rate_cache = {"rate": None, "updated_at": None, "ttl": 3600}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "nbp-currency-service",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/usd-pln-rate")
async def get_usd_pln_rate():
    """Get current USD/PLN rate with caching"""
    
    # Check cache
    if rate_cache["rate"] and rate_cache["updated_at"]:
        cache_age = datetime.now() - rate_cache["updated_at"]
        cache_ttl = timedelta(seconds=int(os.getenv("CACHE_TTL", "7200")))
        
        if cache_age < cache_ttl:
            logger.info(f"Returning cached rate: {rate_cache['rate']}")
            return {
                "rate": rate_cache["rate"],
                "source": "cache",
                "updated_at": rate_cache["updated_at"].isoformat(),
                "cache_age_seconds": cache_age.total_seconds()
            }

    # Fetch fresh rate from NBP API
    try:
        nbp_url = os.getenv("NBP_API_URL", "https://api.nbp.pl/api/exchangerates/rates/a/usd/")
        logger.info(f"Fetching fresh rate from NBP API: {nbp_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                nbp_url,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            rate = data["rates"][0]["mid"]

            # Update cache
            rate_cache["rate"] = rate
            rate_cache["updated_at"] = datetime.now()

            logger.info(f"Fetched fresh rate: {rate}")
            return {
                "rate": rate,
                "source": "nbp_api",
                "updated_at": rate_cache["updated_at"].isoformat(),
                "effective_date": data["rates"][0]["effectiveDate"]
            }

    except Exception as e:
        logger.error(f"NBP API error: {e}")
        
        # Return cached rate if available
        if rate_cache["rate"]:
            logger.warning("Returning cached rate due to API error")
            return {
                "rate": rate_cache["rate"],
                "source": "cache_fallback",
                "updated_at": rate_cache["updated_at"].isoformat(),
                "error": str(e)
            }
        
        raise HTTPException(
            status_code=503, 
            detail=f"NBP API unavailable and no cached rate: {str(e)}"
        )

@app.get("/api/cache-status")
async def get_cache_status():
    """Get cache status for monitoring"""
    if rate_cache["updated_at"]:
        cache_age = datetime.now() - rate_cache["updated_at"]
        return {
            "cached_rate": rate_cache["rate"],
            "updated_at": rate_cache["updated_at"].isoformat(),
            "cache_age_seconds": cache_age.total_seconds(),
            "cache_ttl_seconds": int(os.getenv("CACHE_TTL", "7200"))
        }
    else:
        return {"cached_rate": None, "status": "no_cache"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF

# Expose port
EXPOSE 8001

# Start NBP service
CMD ["python3", "/app/nbp_service.py"]