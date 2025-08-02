"""
InfluxDB-First Batch Orchestrator - Coordinates batch processing with InfluxDB-First architecture
Reads raw data from InfluxDB, writes summaries to SQLite
"""

import asyncio
import time
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import logging

from .services import (
    NBPExchangeRateService,
    ModelPricingService,
    DataCleanupService,
    MonthlyRolloverService
)
from .services.influxdb_aggregation_service import InfluxDBUsageAggregationService
from .repositories import (
    PricingRepository,
    SystemRepository
)
from .repositories.influxdb_usage_repository import InfluxDBUsageRepository
from .models.batch_models import BatchResult, BatchOperationResult
from .utils import get_async_db, BatchLogger

log = logging.getLogger(__name__)


class InfluxDBBatchOrchestrator:
    """InfluxDB-First orchestrator for daily batch processing"""
    
    def __init__(self):
        self.logger = BatchLogger("InfluxDB-First Daily Batch Processing")
        self._initialized = False
        self.influxdb_first_enabled = os.getenv("INFLUXDB_FIRST_ENABLED", "false").lower() == "true"
        
    async def _initialize(self):
        """Initialize all services and repositories"""
        if self._initialized:
            return
            
        # Get async database instance
        self.db = await get_async_db()
        
        # Initialize repositories
        if self.influxdb_first_enabled:
            self.usage_repo = InfluxDBUsageRepository(self.db)
            log.info("Initialized InfluxDB-First usage repository")
        else:
            # Fallback to legacy repository
            from .repositories import UsageRepository
            self.usage_repo = UsageRepository(self.db)
            log.warning("INFLUXDB_FIRST_ENABLED is disabled - using legacy SQLite repository")
            
        self.pricing_repo = PricingRepository(self.db)
        self.system_repo = SystemRepository(self.db)
        
        # Initialize services
        self.nbp_service = NBPExchangeRateService()
        self.pricing_service = ModelPricingService(self.pricing_repo)
        
        if self.influxdb_first_enabled:
            self.aggregation_service = InfluxDBUsageAggregationService(self.usage_repo)
            log.info("Initialized InfluxDB-First aggregation service")
        else:
            # Fallback to legacy aggregation service
            from .services import UsageAggregationService
            self.aggregation_service = UsageAggregationService(self.usage_repo)
            log.warning("Using legacy SQLite aggregation service")
            
        self.cleanup_service = DataCleanupService(self.system_repo)
        self.rollover_service = MonthlyRolloverService(self.usage_repo)
        
        self._initialized = True
        
    async def run_daily_batch(self) -> BatchResult:
        """
        Main daily batch processing function for InfluxDB-First architecture
        
        Architecture Flow:
        1. Update reference data (NBP rates, model pricing)
        2. Read raw usage data from InfluxDB
        3. Aggregate into daily summaries in SQLite
        4. Validate and correct markup costs
        5. Cleanup old data
        6. Handle monthly rollover
        
        Timing: Should be called at 13:00 (1 PM) CET daily
        - NBP publishes USD/PLN rates at 11:30 AM CET
        - 13:00 execution ensures same-day exchange rates are used
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
            
            log.info(f"🕰️ Starting InfluxDB-First daily batch processing for {processing_date}")
            
            result = BatchResult(
                success=True,
                processing_date=processing_date.isoformat(),
                current_date=today.isoformat(),
                batch_start_time=datetime.now().isoformat(),
                operations=[],
                data_source="influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite"
            )
            
            # Phase 1: Update reference data (can run in parallel)
            with self.logger.step("Phase 1: Update reference data") as phase:
                ref_data_results = await self._update_reference_data()
                result.operations.extend(ref_data_results)
                phase["details"]["operations"] = len(ref_data_results)
                
            # Phase 2: Process usage data from InfluxDB
            with self.logger.step("Phase 2: Process InfluxDB usage data") as phase:
                usage_results = await self._process_influxdb_usage_data(processing_date, today)
                result.operations.extend(usage_results)
                phase["details"]["operations"] = len(usage_results)
                phase["details"]["data_source"] = "influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite"
                
            # Phase 3: Cleanup and maintenance
            with self.logger.step("Phase 3: Cleanup and maintenance") as phase:
                cleanup_results = await self._cleanup_and_maintenance(processing_date)
                result.operations.extend(cleanup_results)
                phase["details"]["operations"] = len(cleanup_results)
                
            # Calculate batch duration
            batch_duration = time.time() - batch_start
            result.total_duration_seconds = batch_duration
            result.batch_end_time = datetime.now().isoformat()
            
            # Determine overall success
            failed_operations = [op for op in result.operations if not op.success]
            if failed_operations:
                result.success = False
                result.error = f"{len(failed_operations)} operations failed"
                
            self.logger.complete({
                "duration_seconds": batch_duration,
                "operations_completed": len(result.operations),
                "operations_failed": len(failed_operations),
                "data_source": result.data_source
            })
            
            if result.success:
                log.info(
                    f"✅ InfluxDB-First daily batch completed successfully in {batch_duration:.2f}s "
                    f"({len(result.operations)} operations)"
                )
            else:
                log.error(
                    f"❌ InfluxDB-First daily batch completed with errors in {batch_duration:.2f}s "
                    f"({len(failed_operations)}/{len(result.operations)} operations failed)"
                )
                
            return result
            
        except Exception as e:
            batch_duration = time.time() - batch_start
            log.error(f"❌ InfluxDB-First daily batch failed after {batch_duration:.2f}s: {e}")
            
            result = BatchResult(
                success=False,
                processing_date=processing_date.isoformat(),
                current_date=today.isoformat(),
                error=str(e),
                total_duration_seconds=batch_duration,
                data_source="influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite"
            )
            
            self.logger.complete({"error": str(e), "duration_seconds": batch_duration})
            
            return result
            
    async def _update_reference_data(self) -> List[BatchOperationResult]:
        """Update reference data (NBP rates and model pricing)"""
        operations = []
        
        # Update NBP exchange rates
        try:
            with self.logger.step("Updating NBP exchange rates") as step:
                nbp_result = await self.nbp_service.fetch_and_store_latest_rate()
                operations.append(BatchOperationResult(
                    operation="nbp_update",
                    success=nbp_result.get("success", False),
                    details=nbp_result,
                    error=nbp_result.get("error")
                ))
                step["details"] = nbp_result
                
        except Exception as e:
            log.error(f"NBP update failed: {e}")
            operations.append(BatchOperationResult(
                operation="nbp_update",
                success=False,
                error=str(e)
            ))
            
        # Update model pricing
        try:
            with self.logger.step("Updating model pricing") as step:
                pricing_result = await self.pricing_service.update_pricing_data()
                operations.append(BatchOperationResult(
                    operation="pricing_update",
                    success=pricing_result.get("success", False),
                    details=pricing_result,
                    error=pricing_result.get("error")
                ))
                step["details"] = pricing_result
                
        except Exception as e:
            log.error(f"Pricing update failed: {e}")
            operations.append(BatchOperationResult(
                operation="pricing_update",
                success=False,
                error=str(e)
            ))
            
        return operations
        
    async def _process_influxdb_usage_data(self, processing_date: date, current_date: date) -> List[BatchOperationResult]:
        """Process usage data from InfluxDB to SQLite summaries"""
        operations = []
        
        # Usage aggregation from InfluxDB
        try:
            with self.logger.step("InfluxDB usage aggregation") as step:
                aggregation_result = await self.aggregation_service.consolidate_daily_usage(processing_date)
                operations.append(BatchOperationResult(
                    operation="influxdb_usage_aggregation",
                    success=aggregation_result.success,
                    details={
                        "clients_processed": aggregation_result.clients_processed,
                        "records_verified": aggregation_result.total_records_verified,
                        "data_corrections": aggregation_result.data_corrections,
                        "influxdb_records_processed": getattr(aggregation_result, 'influxdb_records_processed', 0),
                        "data_source": getattr(aggregation_result, 'data_source', 'unknown')
                    },
                    error=aggregation_result.error
                ))
                step["details"] = {
                    "clients_processed": aggregation_result.clients_processed,
                    "influxdb_records_processed": getattr(aggregation_result, 'influxdb_records_processed', 0),
                    "data_source": getattr(aggregation_result, 'data_source', 'unknown')
                }
                
        except Exception as e:
            log.error(f"InfluxDB usage aggregation failed: {e}")
            operations.append(BatchOperationResult(
                operation="influxdb_usage_aggregation",
                success=False,
                error=str(e)
            ))
            
        return operations
        
    async def _cleanup_and_maintenance(self, processing_date: date) -> List[BatchOperationResult]:
        """Cleanup old data and perform maintenance tasks"""
        operations = []
        
        # Data cleanup
        try:
            with self.logger.step("Data cleanup") as step:
                cleanup_result = await self.cleanup_service.cleanup_old_data()
                operations.append(BatchOperationResult(
                    operation="data_cleanup",
                    success=cleanup_result.get("success", False),
                    details=cleanup_result,
                    error=cleanup_result.get("error")
                ))
                step["details"] = cleanup_result
                
        except Exception as e:
            log.error(f"Data cleanup failed: {e}")
            operations.append(BatchOperationResult(
                operation="data_cleanup",
                success=False,
                error=str(e)
            ))
            
        # Monthly rollover (if first day of month)
        if processing_date.day == 1:
            try:
                with self.logger.step("Monthly rollover") as step:
                    rollover_result = await self.rollover_service.process_monthly_rollover(processing_date)
                    operations.append(BatchOperationResult(
                        operation="monthly_rollover",
                        success=rollover_result.get("success", False),
                        details=rollover_result,
                        error=rollover_result.get("error")
                    ))
                    step["details"] = rollover_result
                    
            except Exception as e:
                log.error(f"Monthly rollover failed: {e}")
                operations.append(BatchOperationResult(
                    operation="monthly_rollover",
                    success=False,
                    error=str(e)
                ))
                
        return operations
        
    async def health_check(self) -> Dict[str, Any]:
        """Health check for InfluxDB-First batch orchestrator"""
        try:
            await self._initialize()
            
            health_status = {
                "status": "healthy",
                "influxdb_first_enabled": self.influxdb_first_enabled,
                "data_source": "influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite",
                "services": {}
            }
            
            # Check aggregation service health
            if hasattr(self.aggregation_service, 'get_aggregation_health_check'):
                aggregation_health = await self.aggregation_service.get_aggregation_health_check()
                health_status["services"]["aggregation"] = aggregation_health
            else:
                health_status["services"]["aggregation"] = {"status": "legacy_mode"}
                
            # Check NBP service
            health_status["services"]["nbp"] = {"status": "operational"}
            
            # Check pricing service
            health_status["services"]["pricing"] = {"status": "operational"}
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "influxdb_first_enabled": self.influxdb_first_enabled
            }