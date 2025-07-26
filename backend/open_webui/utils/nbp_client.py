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
        
        Hybrid approach combining holiday calendar optimization with robust fallback:
        - Known Polish holidays: skip API calls, use last working day
        - Weekends: use Friday rate
        - Unknown non-publication days: enhanced 404 fallback search
        - Technical issues: automatic retry with working day search
        
        Returns:
            {
                "rate": 4.0123,           # USD/PLN sell rate
                "effective_date": "2024-01-15",  # Date when rate was published
                "table_no": "012/C/NBP/2024",    # NBP table number
                "rate_source": "current|working_day|holiday_skip|fallback_404"
                "skip_reason": "Known holiday/weekend/etc" # Why API call was skipped
            }
        """
        # Check cache first
        cache_key = "usd_pln_rate"
        cached = self._cache.get(cache_key)
        if cached:
            log.debug(f"Using cached USD/PLN rate: {cached['rate']} from {cached.get('rate_source', 'unknown')}")
            return cached
        
        from .polish_holidays import polish_holidays
        
        now = datetime.now()
        today = date.today()
        nbp_publish_time = datetime.combine(today, datetime_time(8, 15))  # 8:15 AM CET
        
        # TIER 1: Holiday Calendar Optimization
        # Check if we know this day won't have data
        if not polish_holidays.is_working_day(today):
            # Skip API call for known non-working days
            fallback_date = polish_holidays.get_last_working_day_before(today)
            data = await self._fetch_exchange_rate_for_date(fallback_date)
            
            if data:
                skip_reason = "Weekend" if today.weekday() >= 5 else f"Polish holiday: {polish_holidays.get_holiday_name(today)}"
                data.update({
                    'rate_source': 'holiday_skip',
                    'skip_reason': skip_reason,
                    'original_target_date': today.isoformat(),
                    'fallback_date': fallback_date.isoformat()
                })
                
                # Cache with appropriate TTL
                ttl = self._calculate_cache_ttl(data, now, today, nbp_publish_time)
                self._cache.set(cache_key, data, ttl)
                
                log.info(f"🗓️  {skip_reason}: Using rate from {fallback_date} (rate: {data['rate']})")
                return data
        
        # TIER 2: Working Day Strategy with Time Logic
        data = None
        rate_source = "current"
        
        if now < nbp_publish_time:
            # Before 8:15 AM - might not have today's rate yet
            log.debug("Before NBP publish time (8:15 AM)")
            
            # Try today's rate first (might be available)
            data = await self._fetch_exchange_rate_for_date(today)
            
            if not data:
                # No current rate - use previous working day
                fallback_date = polish_holidays.get_last_working_day_before(today)
                data = await self._fetch_exchange_rate_for_date(fallback_date)
                rate_source = "working_day"
                log.info(f"⏰ Before publish time, no current rate: Using {fallback_date}")
        else:
            # After 8:15 AM - current rate should be available
            log.debug("After NBP publish time (8:15 AM)")
            data = await self._fetch_exchange_rate_for_date(today)
            
            if not data:
                log.warning(f"⚠️  No rate available on expected working day {today} after publish time")
                # Fall through to TIER 3 for robust handling
        
        # TIER 3: Enhanced 404 Fallback (handles unknown non-publication days)
        if not data:
            log.info("🔍 Using enhanced fallback search for unknown non-publication day")
            data = await self._enhanced_fallback_search(today)
            if data:
                rate_source = "fallback_404"
        
        if data:
            # Add metadata
            if 'rate_source' not in data:
                data['rate_source'] = rate_source
            
            # Smart caching
            ttl = self._calculate_cache_ttl(data, now, today, nbp_publish_time)
            self._cache.set(cache_key, data, ttl)
            
            log.info(f"✅ USD/PLN rate: {data['rate']} from {data['effective_date']} (source: {data['rate_source']})")
            return data
        
        log.error("❌ Failed to get USD/PLN rate - all strategies exhausted")
        return None
    
    async def _enhanced_fallback_search(self, target_date: date, max_days_back: int = 10) -> Optional[Dict[str, Any]]:
        """
        Enhanced fallback search for unknown non-publication days.
        Handles technical issues, undeclared holidays, bank strikes, etc.
        
        Args:
            target_date: The date we originally wanted data for
            max_days_back: Maximum days to search backwards
            
        Returns:
            Rate data from the most recent available working day
        """
        from .polish_holidays import polish_holidays
        
        log.info(f"🔍 Enhanced fallback search from {target_date} (max {max_days_back} days back)")
        
        # Strategy: Try working days going backwards, skip known non-working days
        days_checked = 0
        current_date = target_date - timedelta(days=1)
        
        while days_checked < max_days_back:
            # Skip weekends and known holidays to avoid unnecessary API calls
            if polish_holidays.is_working_day(current_date):
                log.debug(f"  Trying working day: {current_date}")
                data = await self._fetch_exchange_rate_for_date(current_date)
                
                if data:
                    log.info(f"  ✅ Found rate from {current_date} (fallback from {target_date})")
                    data.update({
                        'fallback_info': {
                            'original_target': target_date.isoformat(),
                            'days_back': (target_date - current_date).days,
                            'reason': 'Unknown non-publication day (404 fallback)'
                        }
                    })
                    return data
                else:
                    log.debug(f"  ❌ No data available for {current_date}")
            else:
                # Skip known non-working day
                skip_reason = "weekend" if current_date.weekday() >= 5 else "holiday"
                log.debug(f"  ⏭️  Skipping {current_date} ({skip_reason})")
            
            current_date -= timedelta(days=1)
            days_checked += 1
        
        log.warning(f"Enhanced fallback search exhausted - no data found within {max_days_back} days")
        return None
    
    def _calculate_cache_ttl(self, data: Dict[str, Any], now: datetime, today: date, nbp_publish_time: datetime) -> timedelta:
        """Calculate appropriate cache TTL based on rate source and timing"""
        rate_source = data.get('rate_source', 'current')
        effective_date = data.get('effective_date')
        
        if rate_source == 'holiday_skip':
            # Holiday or weekend rates - cache until next working day
            from .polish_holidays import polish_holidays
            next_working_day = polish_holidays.get_next_working_day_after(today)
            next_publish_time = datetime.combine(next_working_day, datetime_time(8, 15))
            return max(next_publish_time - now, timedelta(minutes=5))
            
        elif rate_source == 'working_day' and now < nbp_publish_time:
            # Using previous working day before publish time - refresh at publish time
            return max(nbp_publish_time - now, timedelta(minutes=5))
            
        elif rate_source == 'fallback_404':
            # Unknown non-publication day - cache for shorter period to detect recovery
            return timedelta(hours=4)  # Check again in 4 hours
            
        elif effective_date == today.isoformat() and now < nbp_publish_time:
            # Current day rate but before publish time - check again at publish time
            return max(nbp_publish_time - now, timedelta(minutes=5))
            
        else:
            # Standard 24-hour cache for stable current rates
            return timedelta(hours=24)
    
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