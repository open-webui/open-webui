"""
Usage Aggregation Service - Validates and corrects daily usage data
"""

import asyncio
import time
from datetime import date
from typing import List, Tuple, Dict, Any
import logging

from ..models.batch_models import UsageConsolidationResult, ClientConsolidationStats
from ..repositories.usage_repository import UsageRepository
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class UsageAggregationService:
    """Service for aggregating and validating usage data"""
    
    def __init__(self, usage_repo: UsageRepository):
        self.usage_repo = usage_repo
        self.logger = BatchLogger("Usage Aggregation")
        
    async def consolidate_daily_usage(self, processing_date: date) -> UsageConsolidationResult:
        """Validate and correct daily usage data for all clients"""
        self.logger.start()
        
        try:
            # Get all active clients
            with self.logger.step("Loading active clients") as step:
                clients = await self.usage_repo.get_active_clients()
                step["details"]["client_count"] = len(clients)
                
            # Process clients in parallel batches
            batch_size = 10
            all_client_stats = []
            data_corrections = 0
            
            for i in range(0, len(clients), batch_size):
                batch = clients[i:i + batch_size]
                
                with self.logger.step(f"Processing batch {i//batch_size + 1}") as step:
                    # Process batch in parallel
                    tasks = [
                        self._process_client_usage(client_id, client_name, markup_rate, processing_date)
                        for client_id, client_name, markup_rate in batch
                    ]
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect results
                    for result in batch_results:
                        if isinstance(result, Exception):
                            log.error(f"Error processing client: {result}")
                            continue
                            
                        if result:
                            all_client_stats.append(result)
                            if result.markup_cost_corrected:
                                data_corrections += 1
                                
                    step["details"]["clients_processed"] = len(batch)
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
            
            self.logger.complete({
                "clients_processed": result.clients_processed,
                "records_verified": result.total_records_verified,
                "corrections_made": result.data_corrections
            })
            
            log.info(
                f"📊 Daily consolidation completed: {result.clients_processed} clients, "
                f"{result.total_records_verified} records verified, "
                f"{result.data_corrections} corrections made"
            )
            
            return result
            
        except Exception as e:
            log.error(f"❌ Daily consolidation failed: {e}")
            
            result = UsageConsolidationResult(
                success=False,
                processing_date=processing_date.isoformat(),
                error=str(e)
            )
            
            self.logger.complete({"error": str(e)})
            
            return result
            
    async def _process_client_usage(
        self, 
        client_id: int, 
        client_name: str, 
        markup_rate: float, 
        processing_date: date
    ) -> ClientConsolidationStats:
        """Process usage for a single client"""
        # Get daily usage
        usage_data = await self.usage_repo.get_client_daily_usage(client_id, processing_date)
        
        if not usage_data:
            return None
            
        tokens, requests, raw_cost, markup_cost, primary_model = usage_data
        
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
        
        # Correct markup cost if there's a significant difference (> 0.001)
        if cost_diff > 0.001:
            await self.usage_repo.update_markup_cost(
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
                f"${markup_cost:.6f} → ${expected_markup_cost:.6f}"
            )
            
        return client_stats