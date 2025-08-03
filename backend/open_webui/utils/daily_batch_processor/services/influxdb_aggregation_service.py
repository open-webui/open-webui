"""
InfluxDB-First Usage Aggregation Service 
Reads raw data from InfluxDB and creates daily summaries in SQLite
"""

import asyncio
import time
import os
from datetime import date
from typing import List, Tuple, Dict, Any
import logging

from ..models.batch_models import UsageConsolidationResult, ClientConsolidationStats
from ..repositories.influxdb_usage_repository import InfluxDBUsageRepository
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class InfluxDBUsageAggregationService:
    """Service for aggregating usage data from InfluxDB to SQLite summaries"""
    
    def __init__(self, influxdb_usage_repo: InfluxDBUsageRepository):
        self.influxdb_usage_repo = influxdb_usage_repo
        self.logger = BatchLogger("InfluxDB Usage Aggregation")
        
    async def consolidate_daily_usage(self, processing_date: date) -> UsageConsolidationResult:
        """
        Consolidate daily usage from InfluxDB raw data to SQLite summaries
        
        Architecture Flow:
        1. Get active clients from SQLite
        2. For each client, read raw usage from InfluxDB
        3. Aggregate raw data into daily summary
        4. Write/update daily summary in SQLite
        5. Validate markup cost calculations
        """
        self.logger.start()
        
        try:
            # Get all active clients
            with self.logger.step("Loading active clients") as step:
                clients = await self.influxdb_usage_repo.get_active_clients()
                step["details"]["client_count"] = len(clients)
                
            # Process clients in parallel batches
            batch_size = int(os.getenv("INFLUXDB_AGGREGATION_BATCH_SIZE", "5"))  # Smaller batches for InfluxDB queries
            all_client_stats = []
            data_corrections = 0
            influxdb_records_processed = 0
            
            for i in range(0, len(clients), batch_size):
                batch = clients[i:i + batch_size]
                
                with self.logger.step(f"Processing InfluxDB batch {i//batch_size + 1}") as step:
                    # Process batch in parallel
                    tasks = [
                        self._process_client_influxdb_aggregation(client_id, client_name, markup_rate, processing_date)
                        for client_id, client_name, markup_rate in batch
                    ]
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect results
                    for result in batch_results:
                        if isinstance(result, Exception):
                            log.error(f"Error processing client InfluxDB aggregation: {result}")
                            continue
                            
                        if result:
                            all_client_stats.append(result)
                            if result.markup_cost_corrected:
                                data_corrections += 1
                            
                            # Count InfluxDB records processed
                            if hasattr(result, 'raw_records_processed'):
                                influxdb_records_processed += result.raw_records_processed
                                
                    step["details"]["clients_processed"] = len(batch)
                    step["details"]["influxdb_records"] = sum(
                        getattr(r, 'raw_records_processed', 0) 
                        for r in batch_results 
                        if hasattr(r, 'raw_records_processed')
                    )
                    step["details"]["corrections"] = sum(
                        1 for r in batch_results 
                        if isinstance(r, ClientConsolidationStats) and r.markup_cost_corrected
                    )
                    
            # Create final result
            result = UsageConsolidationResult(
                success=True,
                processing_date=processing_date.isoformat(),
                clients_processed=len(clients),
                total_records_verified=len(all_client_stats),
                data_corrections=data_corrections,
                clients_data=all_client_stats
            )
            
            # Add InfluxDB-specific metrics
            result.influxdb_records_processed = influxdb_records_processed
            result.data_source = "influxdb_first"
            
            self.logger.complete({
                "clients_processed": result.clients_processed,
                "records_verified": result.total_records_verified,
                "corrections_made": result.data_corrections,
                "influxdb_records_processed": influxdb_records_processed,
                "data_source": "influxdb_first"
            })
            
            log.info(
                f"📊 InfluxDB-First daily consolidation completed: {result.clients_processed} clients, "
                f"{influxdb_records_processed} InfluxDB records processed, "
                f"{result.total_records_verified} summaries created, "
                f"{result.data_corrections} corrections made"
            )
            
            return result
            
        except Exception as e:
            log.error(f"❌ InfluxDB-First daily consolidation failed: {e}")
            
            result = UsageConsolidationResult(
                success=False,
                processing_date=processing_date.isoformat(),
                error=str(e),
                data_source="influxdb_first"
            )
            
            self.logger.complete({"error": str(e)})
            
            return result
            
    async def _process_client_influxdb_aggregation(
        self, 
        client_id: int, 
        client_name: str, 
        markup_rate: float, 
        processing_date: date
    ) -> ClientConsolidationStats:
        """
        Process InfluxDB aggregation for a single client
        
        Flow:
        1. Read raw usage data from InfluxDB
        2. Aggregate into daily summary
        3. Write/update summary in SQLite
        4. Validate markup cost calculation
        """
        try:
            # Process daily aggregation from InfluxDB to SQLite
            aggregation_result = await self.influxdb_usage_repo.process_client_daily_aggregation(
                client_id, client_name, markup_rate, processing_date
            )
            
            if not aggregation_result or "error" in aggregation_result:
                if aggregation_result and "error" in aggregation_result:
                    log.error(f"Error aggregating data for {client_name}: {aggregation_result['error']}")
                return None
            
            # Extract aggregated data
            aggregated_data = aggregation_result["aggregated_data"]
            raw_records_count = aggregation_result["raw_records_processed"]
            
            tokens = aggregated_data["total_tokens"]
            requests = aggregated_data["total_requests"]
            raw_cost = aggregated_data["raw_cost"]
            markup_cost = aggregated_data["markup_cost"]
            primary_model = aggregated_data["primary_model"]
            
            # Validate markup cost calculation
            expected_markup_cost = raw_cost * markup_rate
            cost_diff = abs(markup_cost - expected_markup_cost)
            
            client_stats = ClientConsolidationStats(
                client_id=client_id,
                client_name=client_name,
                tokens=tokens,
                requests=requests,
                raw_cost=raw_cost,
                markup_cost=markup_cost,
                markup_rate=markup_rate,
                primary_model=primary_model,
                data_validated=True
            )
            
            # Add InfluxDB-specific attributes
            client_stats.raw_records_processed = raw_records_count
            client_stats.data_source = "influxdb_first"
            
            # Correct markup cost if there's a significant difference (> 0.001)
            if cost_diff > 0.001:
                await self.influxdb_usage_repo.update_markup_cost(
                    client_id,
                    processing_date,
                    expected_markup_cost,
                    int(time.time())
                )
                
                client_stats.markup_cost_corrected = {
                    "old_value": markup_cost,
                    "new_value": expected_markup_cost,
                    "difference": cost_diff
                }
                
                log.info(
                    f"💰 Corrected markup cost for {client_name}: "
                    f"${markup_cost:.6f} → ${expected_markup_cost:.6f} "
                    f"(processed {raw_records_count} InfluxDB records)"
                )
                
            return client_stats
            
        except Exception as e:
            log.error(f"Failed to process InfluxDB aggregation for client {client_name}: {e}")
            return None
    
    async def get_aggregation_health_check(self) -> Dict[str, Any]:
        """Health check for InfluxDB aggregation service"""
        try:
            from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service
            
            # Check InfluxDB service health
            influxdb_health = await influxdb_first_service.health_check()
            
            # Check if we have active clients
            clients = await self.influxdb_usage_repo.get_active_clients()
            
            return {
                "status": "healthy",
                "influxdb_service": influxdb_health,
                "active_clients_count": len(clients),
                "data_source": "influxdb_first",
                "aggregation_service": "operational"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "data_source": "influxdb_first",
                "aggregation_service": "error"
            }