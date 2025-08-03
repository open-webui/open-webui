"""
Batch Orchestrator - Coordinates all batch processing services
"""

import asyncio
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import logging

from .services import (
    NBPExchangeRateService,
    ModelPricingService,
    UsageAggregationService,
    DataCleanupService,
    MonthlyRolloverService
)
from .repositories import (
    UsageRepository,
    PricingRepository,
    SystemRepository
)
from .models.batch_models import BatchResult, BatchOperationResult
from .utils import get_async_db, BatchLogger

log = logging.getLogger(__name__)


class BatchOrchestrator:
    """Main orchestrator for daily batch processing"""
    
    def __init__(self):
        self.logger = BatchLogger("Daily Batch Processing")
        self._initialized = False
        
    async def _initialize(self):
        """Initialize all services and repositories"""
        if self._initialized:
            return
            
        # Get async database instance
        self.db = await get_async_db()
        
        # Initialize repositories
        self.usage_repo = UsageRepository(self.db)
        self.pricing_repo = PricingRepository(self.db)
        self.system_repo = SystemRepository(self.db)
        
        # Initialize services
        self.nbp_service = NBPExchangeRateService()
        self.pricing_service = ModelPricingService(self.pricing_repo)
        self.aggregation_service = UsageAggregationService(self.usage_repo)
        self.cleanup_service = DataCleanupService(self.system_repo)
        self.rollover_service = MonthlyRolloverService(self.usage_repo)
        
        self._initialized = True
        
    async def run_daily_batch(self) -> BatchResult:
        """
        Main daily batch processing function
        Should be called at 13:00 (1 PM) CET daily via cron or scheduler
        
        Timing rationale:
        - NBP publishes USD/PLN rates at 11:30 AM CET based on 11:00 AM calculations
        - 13:00 execution ensures same-day exchange rates are used for daily cost conversion
        - Eliminates 1-day lag where Monday's costs used Friday's rates
        """
        batch_start = time.time()
        self.logger.start()
        
        try:
            # Initialize services
            await self._initialize()
            
            # Process yesterday's COMPLETE data
            today = date.today()
            yesterday = today - timedelta(days=1)
            processing_date = yesterday
            
            log.info(f"🕰️ Starting daily batch processing for {processing_date}")
            
            result = BatchResult(
                success=True,
                processing_date=processing_date.isoformat(),
                current_date=today.isoformat(),
                batch_start_time=datetime.now().isoformat(),
                operations=[]
            )
            
            # Phase 1: Update reference data (can run in parallel)
            with self.logger.step("Phase 1: Update reference data") as phase:
                ref_data_results = await self._update_reference_data()
                result.operations.extend(ref_data_results)
                phase["details"]["operations"] = len(ref_data_results)
                
            # Phase 2: Process usage data (sequential due to dependencies)
            with self.logger.step("Phase 2: Process usage data") as phase:
                usage_results = await self._process_usage_data(processing_date, today)
                result.operations.extend(usage_results)
                phase["details"]["operations"] = len(usage_results)
                
            # Phase 3: Cleanup operations
            with self.logger.step("Phase 3: Cleanup operations") as phase:
                cleanup_results = await self._perform_cleanup()
                result.operations.extend(cleanup_results)
                phase["details"]["operations"] = len(cleanup_results)
                
            # Calculate final metrics
            batch_duration = time.time() - batch_start
            result.batch_duration_seconds = round(batch_duration, 3)
            result.completed_at = datetime.now().isoformat()
            
            # Log summary
            successful_ops = sum(1 for op in result.operations if op.success)
            total_ops = len(result.operations)
            
            log.info(
                f"✅ Daily batch processing completed: {successful_ops}/{total_ops} "
                f"operations successful in {batch_duration:.2f}s"
            )
            
            # Record batch run
            await self.system_repo.record_batch_run(result.model_dump())
            
            self.logger.complete({
                "successful_operations": successful_ops,
                "total_operations": total_ops,
                "duration_seconds": batch_duration
            })
            
            return result
            
        except Exception as e:
            log.error(f"❌ Daily batch processing failed: {e}")
            
            error_result = BatchResult(
                success=False,
                processing_date=processing_date.isoformat() if 'processing_date' in locals() else None,
                current_date=date.today().isoformat(),
                batch_start_time=datetime.now().isoformat(),
                batch_duration_seconds=time.time() - batch_start,
                error=str(e)
            )
            
            self.logger.complete({"error": str(e)})
            
            return error_result
            
    async def _update_reference_data(self) -> List[BatchOperationResult]:
        """Update reference data (exchange rates and pricing) in parallel"""
        operations = []
        
        # Run NBP and pricing updates in parallel
        tasks = [
            self.nbp_service.update_exchange_rates(),
            self.pricing_service.update_model_pricing()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process NBP result
        if isinstance(results[0], Exception):
            operations.append(BatchOperationResult(
                success=False,
                operation="exchange_rate_update",
                error=str(results[0])
            ))
        else:
            operations.append(BatchOperationResult(
                success=results[0].success,
                operation="exchange_rate_update",
                details=results[0].model_dump()
            ))
            
        # Process pricing result
        if isinstance(results[1], Exception):
            operations.append(BatchOperationResult(
                success=False,
                operation="model_pricing_update",
                error=str(results[1])
            ))
        else:
            operations.append(BatchOperationResult(
                success=results[1].success,
                operation="model_pricing_update",
                details=results[1].model_dump()
            ))
            
        return operations
        
    async def _process_usage_data(
        self, 
        processing_date: date, 
        current_date: date
    ) -> List[BatchOperationResult]:
        """Process usage data (aggregation and monthly totals)"""
        operations = []
        
        # Validate and correct daily usage
        validation_result = await self.aggregation_service.consolidate_daily_usage(processing_date)
        operations.append(BatchOperationResult(
            success=validation_result.success,
            operation="daily_validation",
            details=validation_result.model_dump()
        ))
        
        # Update monthly totals only if validation succeeded
        if validation_result.success:
            monthly_result = await self.rollover_service.update_monthly_totals(current_date)
            operations.append(BatchOperationResult(
                success=monthly_result.success,
                operation="monthly_totals_update",
                details=monthly_result.model_dump()
            ))
        else:
            log.warning("Skipping monthly totals update due to validation failure")
            
        return operations
        
    async def _perform_cleanup(self) -> List[BatchOperationResult]:
        """Perform cleanup operations"""
        operations = []
        
        cleanup_result = await self.cleanup_service.cleanup_old_data()
        operations.append(BatchOperationResult(
            success=cleanup_result.success,
            operation="data_cleanup",
            details=cleanup_result.model_dump()
        ))
        
        return operations


# Module-level function for backward compatibility
async def run_daily_batch() -> Dict[str, Any]:
    """
    Entry point for daily batch processing
    Should be scheduled for 13:00 (1 PM) CET daily to align with NBP exchange rate publication
    """
    orchestrator = BatchOrchestrator()
    result = await orchestrator.run_daily_batch()
    return result.model_dump()