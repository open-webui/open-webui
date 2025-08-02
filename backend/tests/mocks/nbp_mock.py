"""
NBP Mock Service for E2E Testing
Simulates the NBP service with controlled exchange rates for predictable testing
"""

import asyncio
from datetime import date, datetime
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class NBPMockService:
    """Mock NBP service that returns controlled exchange rates for testing"""
    
    def __init__(self):
        self.mock_rates: Dict[str, Decimal] = {}
        self.default_rate = Decimal("4.0")  # Default fallback rate
        self.is_enabled = False
        
    def set_mock_rate(self, date_str: str, rate: Decimal):
        """Set a specific exchange rate for a given date"""
        self.mock_rates[date_str] = rate
        logger.info(f"NBP Mock: Set rate for {date_str} = {rate} PLN/USD")
    
    def enable_mock(self):
        """Enable mock mode"""
        self.is_enabled = True
        logger.info("NBP Mock: Enabled")
    
    def disable_mock(self):
        """Disable mock mode"""
        self.is_enabled = False
        self.mock_rates.clear()
        logger.info("NBP Mock: Disabled")
    
    async def get_usd_pln_rate(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Mock implementation of NBP rate fetching
        
        Args:
            target_date: Date for which to get the rate (default: today)
            
        Returns:
            Mock NBP rate response
        """
        if not self.is_enabled:
            raise Exception("NBP mock is not enabled")
        
        if not target_date:
            target_date = date.today()
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Return mock rate if configured, otherwise use default
        rate = self.mock_rates.get(date_str, self.default_rate)
        
        return {
            "rate": float(rate),
            "effective_date": date_str,
            "rate_source": "mock",
            "table_no": "001/A/NBP/2025",
            "currency": "USD",
            "code": "USD",
            "mid": float(rate)
        }
    
    def get_configured_rates(self) -> Dict[str, Decimal]:
        """Get all configured mock rates for debugging"""
        return self.mock_rates.copy()
    
    def clear_rates(self):
        """Clear all configured rates"""
        self.mock_rates.clear()
        logger.info("NBP Mock: Cleared all configured rates")


# Global mock instance
nbp_mock = NBPMockService()


async def mock_get_current_usd_pln_rate() -> Decimal:
    """Mock implementation of get_current_usd_pln_rate"""
    if not nbp_mock.is_enabled:
        raise Exception("NBP mock is not enabled")
    
    rate_data = await nbp_mock.get_usd_pln_rate()
    return Decimal(str(rate_data["rate"]))


async def mock_get_exchange_rate_info() -> Dict[str, Any]:
    """Mock implementation of get_exchange_rate_info"""
    if not nbp_mock.is_enabled:
        raise Exception("NBP mock is not enabled")
    
    rate_data = await nbp_mock.get_usd_pln_rate()
    
    return {
        "rate": rate_data["rate"],
        "effective_date": rate_data["effective_date"],
        "rate_source": "mock_nbp",
        "last_updated": datetime.now().isoformat(),
        "cached": False,
        "cache_expires": None
    }


async def mock_convert_usd_to_pln(usd_amount: float) -> Dict[str, Any]:
    """Mock implementation of convert_usd_to_pln"""
    if not nbp_mock.is_enabled:
        raise Exception("NBP mock is not enabled")
    
    rate_data = await nbp_mock.get_usd_pln_rate()
    rate = Decimal(str(rate_data["rate"]))
    usd_decimal = Decimal(str(usd_amount))
    pln_amount = usd_decimal * rate
    
    return {
        "usd": float(usd_decimal),
        "pln": float(pln_amount),
        "rate": float(rate),
        "rate_source": "mock_nbp",
        "conversion_date": rate_data["effective_date"]
    }


class NBPMockHTTPService:
    """Mock HTTP service that simulates NBP microservice responses"""
    
    def __init__(self, mock_service: NBPMockService):
        self.mock_service = mock_service
    
    async def get_rate_response(self, date_param: str) -> Dict[str, Any]:
        """
        Simulate HTTP response from NBP microservice
        
        Args:
            date_param: Date parameter (YYYY-MM-DD format)
            
        Returns:
            HTTP response-like dictionary
        """
        if not self.mock_service.is_enabled:
            return {
                "status_code": 503,
                "error": "NBP mock service not enabled"
            }
        
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            rate_data = await self.mock_service.get_usd_pln_rate(target_date)
            
            return {
                "status_code": 200,
                "json": rate_data
            }
            
        except ValueError:
            return {
                "status_code": 400,
                "error": f"Invalid date format: {date_param}"
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": str(e)
            }


# Global HTTP mock instance
nbp_http_mock = NBPMockHTTPService(nbp_mock)


# Context manager for easy mock setup and teardown
class NBPMockContext:
    """Context manager for NBP mock setup and cleanup"""
    
    def __init__(self, test_rates: Optional[Dict[str, float]] = None):
        self.test_rates = test_rates or {}
    
    def __enter__(self):
        nbp_mock.enable_mock()
        
        # Set up test rates
        for date_str, rate in self.test_rates.items():
            nbp_mock.set_mock_rate(date_str, Decimal(str(rate)))
        
        return nbp_mock
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        nbp_mock.disable_mock()


# Convenience function for E2E tests
def setup_nbp_mock_for_e2e_test():
    """Set up NBP mock with standard E2E test configuration"""
    nbp_mock.enable_mock()
    
    # Standard E2E test rate: 4.50 PLN/USD for August 1, 2025
    nbp_mock.set_mock_rate("2025-08-01", Decimal("4.50"))
    
    # Also set rates for surrounding dates to handle weekend logic
    nbp_mock.set_mock_rate("2025-07-31", Decimal("4.50"))
    nbp_mock.set_mock_rate("2025-08-02", Decimal("4.50"))
    nbp_mock.set_mock_rate("2025-08-03", Decimal("4.50"))
    
    logger.info("NBP Mock: Configured for E2E test with 4.50 PLN/USD rate")


if __name__ == "__main__":
    # Test the mock service
    async def test_mock():
        print("Testing NBP Mock Service...")
        
        with NBPMockContext({"2025-08-01": 4.50}) as mock:
            rate_data = await mock.get_usd_pln_rate(date(2025, 8, 1))
            print(f"Mock rate: {rate_data}")
            
            conversion = await mock_convert_usd_to_pln(0.15)
            print(f"Conversion: {conversion}")
        
        print("NBP Mock test completed!")
    
    asyncio.run(test_mock())