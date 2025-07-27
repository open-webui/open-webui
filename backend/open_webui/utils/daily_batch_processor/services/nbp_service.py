"""
NBP Exchange Rate Service - Updates currency exchange rates
"""

from datetime import datetime
import logging
from typing import Dict, Any

from open_webui.utils.currency_converter import get_exchange_rate_info
from ..models.batch_models import ExchangeRateResult
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class NBPExchangeRateService:
    """Service for updating NBP exchange rates"""
    
    def __init__(self):
        self.logger = BatchLogger("NBP Exchange Rate Update")
        
    async def update_exchange_rates(self) -> ExchangeRateResult:
        """Update exchange rates from NBP API with holiday-aware logic"""
        self.logger.start()
        
        try:
            with self.logger.step("Fetching NBP rates") as step:
                # Get fresh exchange rate with holiday-aware logic
                exchange_info = await get_exchange_rate_info()
                
                step["details"]["exchange_info"] = exchange_info
                
                # Create result
                result = ExchangeRateResult(
                    success=True,
                    usd_pln_rate=exchange_info.get("usd_pln", 4.0),
                    effective_date=exchange_info.get("effective_date"),
                    rate_source=exchange_info.get("rate_source", "unknown"),
                    fetched_at=datetime.now().isoformat()
                )
                
                log.info(
                    f"💱 Exchange rates updated: 1 USD = {result.usd_pln_rate} PLN "
                    f"(source: {result.rate_source})"
                )
                
                self.logger.complete({
                    "rate": result.usd_pln_rate,
                    "source": result.rate_source
                })
                
                return result
                
        except Exception as e:
            # Fallback to default rate on error
            log.warning(f"⚠️ NBP API unavailable: {e}, using fallback rate")
            
            result = ExchangeRateResult(
                success=True,  # Success with fallback
                usd_pln_rate=4.0,
                effective_date=datetime.now().date().isoformat(),
                rate_source="fallback_nbp_unavailable",
                error=str(e),
                fetched_at=datetime.now().isoformat()
            )
            
            self.logger.complete({
                "rate": result.usd_pln_rate,
                "source": "fallback",
                "error": str(e)
            })
            
            return result