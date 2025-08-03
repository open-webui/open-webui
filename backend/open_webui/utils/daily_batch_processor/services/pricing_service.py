"""
Model Pricing Service - Updates OpenRouter model pricing
"""

from datetime import datetime
import logging
from typing import Dict, Any

from open_webui.utils.openrouter_models import get_dynamic_model_pricing
from ..models.batch_models import PricingUpdateResult
from ..repositories.pricing_repository import PricingRepository
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class ModelPricingService:
    """Service for updating model pricing from OpenRouter"""
    
    def __init__(self, pricing_repo: PricingRepository):
        self.pricing_repo = pricing_repo
        self.logger = BatchLogger("Model Pricing Update")
        
    async def update_model_pricing(self) -> PricingUpdateResult:
        """Update model pricing from OpenRouter API"""
        self.logger.start()
        
        try:
            with self.logger.step("Fetching OpenRouter pricing") as step:
                # Force refresh to get latest pricing
                pricing_data = await get_dynamic_model_pricing(force_refresh=True)
                
                step["details"]["models_count"] = len(pricing_data.get("models", []))
                step["details"]["source"] = pricing_data.get("source", "unknown")
                
                # Update cache
                await self.pricing_repo.update_pricing_cache(pricing_data)
                
                # Store snapshot for audit
                await self.pricing_repo.store_pricing_snapshot(pricing_data)
                
                result = PricingUpdateResult(
                    success=pricing_data.get("success", False),
                    models_count=len(pricing_data.get("models", [])),
                    source=pricing_data.get("source", "unknown"),
                    last_updated=pricing_data.get("last_updated"),
                    fetched_at=datetime.now().isoformat()
                )
                
                if result.success:
                    log.info(
                        f"💰 Model pricing updated: {result.models_count} models "
                        f"from {result.source}"
                    )
                else:
                    log.warning("⚠️ Model pricing update failed, using cached/fallback data")
                
                self.logger.complete({
                    "models_count": result.models_count,
                    "source": result.source
                })
                
                return result
                
        except Exception as e:
            log.error(f"❌ Failed to update model pricing: {e}")
            
            result = PricingUpdateResult(
                success=False,
                models_count=0,
                error=str(e),
                fetched_at=datetime.now().isoformat()
            )
            
            self.logger.complete({"error": str(e)})
            
            return result