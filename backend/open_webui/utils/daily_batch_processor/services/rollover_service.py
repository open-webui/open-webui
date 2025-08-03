"""
Monthly Rollover Service - Calculates cumulative monthly totals
"""

import asyncio
from datetime import date
from typing import List, Dict, Any
import logging

from ..models.batch_models import MonthlyTotalsResult, ClientMonthlyStats
from ..repositories.usage_repository import UsageRepository
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class MonthlyRolloverService:
    """Service for calculating monthly usage totals"""
    
    def __init__(self, usage_repo: UsageRepository):
        self.usage_repo = usage_repo
        self.logger = BatchLogger("Monthly Rollover")
        
    async def update_monthly_totals(self, current_date: date) -> MonthlyTotalsResult:
        """Update cumulative monthly totals from 1st to current day"""
        self.logger.start()
        
        try:
            # Get month boundaries
            month_start = current_date.replace(day=1)
            
            with self.logger.step("Loading active clients") as step:
                clients = await self.usage_repo.get_active_clients()
                step["details"]["client_count"] = len(clients)
                
            # Process clients in parallel
            batch_size = 10
            all_summaries = []
            
            for i in range(0, len(clients), batch_size):
                batch = clients[i:i + batch_size]
                
                with self.logger.step(f"Processing batch {i//batch_size + 1}") as step:
                    tasks = [
                        self._calculate_client_monthly_stats(
                            client_id, client_name, month_start, current_date
                        )
                        for client_id, client_name, _ in batch
                    ]
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect valid results
                    for result in batch_results:
                        if isinstance(result, Exception):
                            log.error(f"Error calculating monthly stats: {result}")
                            continue
                        if result:
                            all_summaries.append(result)
                            
                    step["details"]["clients_processed"] = len(batch)
                    step["details"]["summaries_created"] = sum(
                        1 for r in batch_results 
                        if isinstance(r, ClientMonthlyStats)
                    )
                    
            # Calculate overall totals
            total_tokens = sum(s.total_tokens for s in all_summaries)
            total_cost = sum(s.total_markup_cost for s in all_summaries)
            
            result = MonthlyTotalsResult(
                success=True,
                processing_date=current_date.isoformat(),
                month_range=f"{month_start.isoformat()} to {current_date.isoformat()}",
                clients_processed=len(clients),
                monthly_summaries=all_summaries,
                overall_totals={
                    "total_tokens": total_tokens,
                    "total_markup_cost": total_cost,
                    "active_clients": len(all_summaries)
                }
            )
            
            self.logger.complete({
                "clients_processed": result.clients_processed,
                "active_clients": len(all_summaries),
                "total_tokens": total_tokens,
                "total_cost": total_cost
            })
            
            log.info(
                f"📊 Monthly totals updated: {len(all_summaries)} active clients, "
                f"{total_tokens:,} total tokens, ${total_cost:.6f} total cost"
            )
            
            return result
            
        except Exception as e:
            log.error(f"❌ Monthly totals update failed: {e}")
            
            result = MonthlyTotalsResult(
                success=False,
                processing_date=current_date.isoformat(),
                month_range=f"{month_start.isoformat()} to {current_date.isoformat()}",
                error=str(e)
            )
            
            self.logger.complete({"error": str(e)})
            
            return result
            
    async def _calculate_client_monthly_stats(
        self,
        client_id: int,
        client_name: str,
        month_start: date,
        current_date: date
    ) -> ClientMonthlyStats:
        """Calculate monthly statistics for a single client"""
        # Get monthly usage summary
        summary = await self.usage_repo.get_monthly_usage_summary(
            client_id, month_start, current_date
        )
        
        if not summary or summary[0] == 0:  # No usage data
            return None
            
        (days_with_usage, total_tokens, total_requests, total_raw_cost, 
         total_markup_cost, avg_daily, max_daily, last_usage) = summary
        
        # Calculate usage percentage
        days_in_month = current_date.day
        usage_percentage = (days_with_usage / days_in_month * 100) if days_in_month > 0 else 0
        
        # Get most used model
        most_used_model = await self.usage_repo.get_most_used_model(
            client_id, month_start, current_date
        )
        
        return ClientMonthlyStats(
            client_id=client_id,
            client_name=client_name,
            days_with_usage=days_with_usage,
            days_in_month=days_in_month,
            usage_percentage=round(usage_percentage, 1),
            total_tokens=total_tokens or 0,
            total_requests=total_requests or 0,
            total_raw_cost=total_raw_cost or 0.0,
            total_markup_cost=total_markup_cost or 0.0,
            average_daily_tokens=round(avg_daily or 0),
            max_daily_tokens=max_daily or 0,
            most_used_model=most_used_model,
            last_usage_date=last_usage
        )