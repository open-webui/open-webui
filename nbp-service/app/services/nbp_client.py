"""
NBP API Client with mock mode support
"""
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os
import random

from ..models import ExchangeRateResponse
from ..config import settings

logger = logging.getLogger(__name__)


class NBPClient:
    """Client for fetching USD/PLN rates from NBP API or mock data"""
    
    def __init__(self, mock_mode: bool = False, cache_service=None):
        self.mock_mode = mock_mode or settings.mock_mode
        self.cache_service = cache_service
        self.nbp_api_url = settings.nbp_api_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
        self.max_retries = settings.max_retries
        
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"Accept": "application/json"}
            )
    
    async def get_rate(self, date: Optional[str] = None) -> ExchangeRateResponse:
        """
        Get USD/PLN exchange rate for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format. If None, returns current rate.
        """
        if self.mock_mode:
            return self._get_mock_rate(date)
        
        # Check cache first
        cache_key = f"usd_pln_{date or 'current'}"
        if self.cache_service:
            cached = self.cache_service.get(cache_key)
            if cached:
                return cached
        
        # Fetch from NBP API with retry logic
        await self._ensure_session()
        
        for attempt in range(self.max_retries):
            try:
                url = self.nbp_api_url
                if date:
                    url = f"{url}{date}/"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data['rates'][0]['mid']
                        rate_date = data['rates'][0]['effectiveDate']
                        
                        result = ExchangeRateResponse(
                            currency="USD",
                            rate=rate,
                            date=rate_date,
                            source="nbp"
                        )
                        
                        # Cache the result
                        if self.cache_service:
                            if hasattr(self.cache_service, 'set'):
                                self.cache_service.set(cache_key, result, ttl=settings.cache_ttl)
                            else:
                                await self.cache_service.set(cache_key, result, ttl=settings.cache_ttl)
                        
                        logger.info(f"Successfully fetched rate for {date or 'current'}: {rate} PLN")
                        return result
                    
                    elif response.status == 404 and date:
                        # No data for this date (weekend/holiday)
                        logger.warning(f"No NBP data for date {date}, trying previous day")
                        prev_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                        return await self.get_rate(prev_date)
                    
                    else:
                        logger.error(f"NBP API returned status {response.status}")
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching from NBP API (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Error fetching from NBP API (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries failed, fallback to mock data
        logger.warning("All NBP API attempts failed, using mock data")
        return self._get_mock_rate(date)
    
    async def get_rates_range(self, start_date: str, end_date: str) -> List[ExchangeRateResponse]:
        """Get exchange rates for a date range"""
        if self.mock_mode:
            return self._get_mock_rates_range(start_date, end_date)
        
        # For production, implement NBP table API call
        # For now, return mock data
        return self._get_mock_rates_range(start_date, end_date)
    
    def _get_mock_rate(self, date: Optional[str] = None) -> ExchangeRateResponse:
        """Generate mock exchange rate data"""
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now()
        
        # Generate realistic rate based on date (for consistency)
        base_rate = 4.0
        day_offset = target_date.toordinal() % 100
        rate_variation = (day_offset % 20 - 10) * 0.01  # +/- 0.10 PLN variation
        rate = round(base_rate + rate_variation, 4)
        
        return ExchangeRateResponse(
            currency="USD",
            rate=rate,
            date=target_date.strftime("%Y-%m-%d"),
            source="mock"
        )
    
    def _get_mock_rates_range(self, start_date: str, end_date: str) -> List[ExchangeRateResponse]:
        """Generate mock exchange rates for a date range"""
        rates = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current <= end:
            # Skip weekends (NBP doesn't publish rates on weekends)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                rates.append(self._get_mock_rate(current.strftime("%Y-%m-%d")))
            current += timedelta(days=1)
        
        return rates
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()