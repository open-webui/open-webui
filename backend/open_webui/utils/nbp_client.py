import aiohttp
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, date, time as datetime_time, timedelta
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("NBP_CLIENT", logging.INFO))

NBP_API_BASE = "https://api.nbp.pl/api"


class ExchangeRateCache:
    """Simple in-memory cache for exchange rates with TTL"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._ttl = timedelta(hours=24)  # Default TTL of 24 hours
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired"""
        if key in self._cache:
            cached = self._cache[key]
            if datetime.now() < cached['expires_at']:
                return cached['data']
            else:
                # Clean up expired entry
                del self._cache[key]
        return None
    
    def set(self, key: str, data: Dict[str, Any], ttl: Optional[timedelta] = None):
        """Set cache value with expiration"""
        expires_at = datetime.now() + (ttl or self._ttl)
        self._cache[key] = {
            'data': data,
            'expires_at': expires_at
        }
    
    def clear(self):
        """Clear all cached values"""
        self._cache.clear()


class NBPClient:
    """NBP (National Bank of Poland) API client for currency exchange rates"""
    
    def __init__(self):
        self._cache = ExchangeRateCache()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make HTTP request to NBP API"""
        await self._ensure_session()
        
        url = f"{NBP_API_BASE}{endpoint}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "mAI/1.0"
        }
        
        try:
            async with self._session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    # No data available (e.g., weekend/holiday)
                    log.info(f"No NBP data available for {endpoint}")
                    return None
                else:
                    log.error(f"NBP API error: {response.status} for {endpoint}")
                    return None
        except aiohttp.ClientError as e:
            log.error(f"NBP API request failed: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error calling NBP API: {e}")
            return None
    
    async def get_usd_pln_rate(self) -> Optional[Dict[str, Any]]:
        """
        Get current USD/PLN exchange rate from NBP Table C (buy/sell rates)
        Returns the sell (ask) rate which is used for converting USD to PLN
        
        Returns:
            {
                "rate": 4.0123,           # USD/PLN sell rate
                "effective_date": "2024-01-15",  # Date when rate was published
                "table_no": "012/C/NBP/2024"     # NBP table number
            }
        """
        # Check cache first
        cache_key = "usd_pln_rate"
        cached = self._cache.get(cache_key)
        if cached:
            log.debug(f"Using cached USD/PLN rate: {cached['rate']}")
            return cached
        
        # Try to get today's rate
        today = date.today()
        data = await self._fetch_exchange_rate_for_date(today)
        
        if not data:
            # If today's rate not available (weekend/holiday), try previous days
            for days_back in range(1, 8):  # Check up to 7 days back
                check_date = today - timedelta(days=days_back)
                data = await self._fetch_exchange_rate_for_date(check_date)
                if data:
                    log.info(f"Using USD/PLN rate from {check_date} (latest available)")
                    break
        
        if data:
            # Cache the result
            # If it's today's data and before 8:15 AM CET, cache only until 8:15 AM
            # Otherwise cache for 24 hours
            now = datetime.now()
            if data['effective_date'] == today.isoformat():
                nbp_update_time = datetime.combine(today, datetime_time(8, 15))  # 8:15 AM CET
                if now < nbp_update_time:
                    ttl = nbp_update_time - now
                else:
                    ttl = timedelta(hours=24)
            else:
                # Historical rate, cache for 24 hours
                ttl = timedelta(hours=24)
            
            self._cache.set(cache_key, data, ttl)
            return data
        
        log.error("Failed to get USD/PLN rate from NBP")
        return None
    
    async def _fetch_exchange_rate_for_date(self, check_date: date) -> Optional[Dict[str, Any]]:
        """Fetch exchange rate for a specific date"""
        # Format: /exchangerates/tables/c/2024-01-15/
        endpoint = f"/exchangerates/tables/c/{check_date.isoformat()}/"
        
        response = await self._make_request(endpoint)
        if response and isinstance(response, list) and len(response) > 0:
            table = response[0]
            rates = table.get('rates', [])
            
            # Find USD rate
            for rate in rates:
                if rate.get('code') == 'USD':
                    return {
                        'rate': rate.get('ask'),  # Sell rate (for buying PLN with USD)
                        'effective_date': table.get('effectiveDate'),
                        'table_no': table.get('no'),
                        'bid': rate.get('bid'),   # Buy rate (informational)
                        'trading_date': table.get('tradingDate')
                    }
        
        return None
    
    async def convert_usd_to_pln(self, usd_amount: float) -> Optional[Dict[str, Any]]:
        """
        Convert USD amount to PLN using current exchange rate
        
        Returns:
            {
                "usd": 100.00,
                "pln": 401.23,
                "rate": 4.0123,
                "effective_date": "2024-01-15"
            }
        """
        rate_data = await self.get_usd_pln_rate()
        if not rate_data or not rate_data.get('rate'):
            return None
        
        pln_amount = usd_amount * rate_data['rate']
        
        return {
            'usd': usd_amount,
            'pln': round(pln_amount, 2),
            'rate': rate_data['rate'],
            'effective_date': rate_data['effective_date']
        }


# Global singleton instance
nbp_client = NBPClient()