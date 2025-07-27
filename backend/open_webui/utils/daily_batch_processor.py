#!/usr/bin/env python3
"""
Daily Batch Processor for mAI Usage Tracking
Runs at 00:00 daily to validate and aggregate usage data with NBP exchange rates

This script:
1. Updates NBP exchange rates for PLN conversion
2. Updates model pricing from OpenRouter API
3. Validates and corrects previous day's usage data
4. Updates cumulative monthly totals (1st to current day)
5. Cleans up old processed generation records
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

from open_webui.config import DATA_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class DailyBatchProcessor:
    """Daily batch processor for usage data aggregation"""
    
    def __init__(self):
        self.db_path = f"{DATA_DIR}/webui.db"
        
    async def run_daily_batch(self) -> Dict[str, Any]:
        """
        Main daily batch processing function
        Should be called at 00:00 daily via cron or scheduler
        """
        batch_start = time.time()
        log.info("🕰️ Starting daily batch processing for mAI usage tracking")
        
        try:
            # Process yesterday's COMPLETE data (proper production logic)
            # This ensures data integrity and complete daily summaries for monthly counting
            today = date.today()
            yesterday = today - timedelta(days=1)
            processing_date = yesterday  # Always process complete previous day data
            
            results = {
                "success": True,
                "processing_date": processing_date.isoformat(),
                "current_date": today.isoformat(),
                "batch_start_time": datetime.now().isoformat(),
                "operations": []
            }
            
            # 1. Update exchange rates for PLN conversion
            exchange_result = await self._update_exchange_rates()
            results["operations"].append({
                "operation": "exchange_rate_update",
                "success": exchange_result["success"],
                "details": exchange_result
            })
            
            # 2. Update model pricing from OpenRouter
            pricing_result = await self._update_model_pricing()
            results["operations"].append({
                "operation": "model_pricing_update",
                "success": pricing_result["success"],
                "details": pricing_result
            })
            
            # 3. Validate and correct daily usage data
            validation_result = await self._consolidate_daily_usage(processing_date)
            results["operations"].append({
                "operation": "daily_validation", 
                "success": validation_result["success"],
                "details": validation_result
            })
            
            # 4. Update monthly cumulative totals (1st to current day)
            monthly_result = await self._update_monthly_totals(today)
            results["operations"].append({
                "operation": "monthly_totals_update",
                "success": monthly_result["success"], 
                "details": monthly_result
            })
            
            # 5. Clean up old processed generations
            cleanup_result = await self._cleanup_old_data()
            results["operations"].append({
                "operation": "data_cleanup",
                "success": cleanup_result["success"],
                "details": cleanup_result
            })
            
            # Calculate batch processing time
            batch_duration = time.time() - batch_start
            results["batch_duration_seconds"] = round(batch_duration, 3)
            results["completed_at"] = datetime.now().isoformat()
            
            # Log summary
            successful_ops = sum(1 for op in results["operations"] if op["success"])
            total_ops = len(results["operations"])
            
            log.info(f"✅ Daily batch processing completed: {successful_ops}/{total_ops} operations successful in {batch_duration:.2f}s")
            
            return results
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "processing_date": processing_date.isoformat() if 'processing_date' in locals() else None,
                "batch_duration_seconds": time.time() - batch_start,
                "failed_at": datetime.now().isoformat()
            }
            
            log.error(f"❌ Daily batch processing failed: {e}")
            return error_result
    
    async def _update_exchange_rates(self) -> Dict[str, Any]:
        """Update NBP exchange rates for accurate PLN conversion"""
        try:
            from open_webui.utils.currency_converter import get_exchange_rate_info
            
            # Get fresh exchange rate with holiday-aware logic
            exchange_info = await get_exchange_rate_info()
            
            # Store rate info for the day (could be stored in a rates table if needed)
            rate_result = {
                "success": True,
                "usd_pln_rate": exchange_info.get("usd_pln", 4.0),
                "effective_date": exchange_info.get("effective_date"),
                "rate_source": exchange_info.get("rate_source", "unknown"),
                "fetched_at": datetime.now().isoformat()
            }
            
            log.info(f"💱 Exchange rates updated: 1 USD = {rate_result['usd_pln_rate']} PLN (source: {rate_result['rate_source']})")
            
            return rate_result
            
        except Exception as e:
            fallback_result = {
                "success": True,  # Success with fallback
                "usd_pln_rate": 4.0,  # Fallback rate
                "effective_date": date.today().isoformat(),
                "rate_source": "fallback_nbp_unavailable", 
                "error": str(e),
                "fetched_at": datetime.now().isoformat()
            }
            
            log.warning(f"⚠️ NBP API unavailable, using fallback rate: {fallback_result['usd_pln_rate']} PLN")
            return fallback_result
    
    async def _update_model_pricing(self) -> Dict[str, Any]:
        """Update model pricing from OpenRouter API"""
        try:
            from open_webui.utils.openrouter_models import get_dynamic_model_pricing
            
            # Force refresh to get latest pricing
            pricing_data = await get_dynamic_model_pricing(force_refresh=True)
            
            pricing_result = {
                "success": pricing_data.get("success", False),
                "models_count": len(pricing_data.get("models", [])),
                "source": pricing_data.get("source", "unknown"),
                "last_updated": pricing_data.get("last_updated"),
                "fetched_at": datetime.now().isoformat()
            }
            
            if pricing_result["success"]:
                log.info(f"💰 Model pricing updated: {pricing_result['models_count']} models from {pricing_result['source']}")
            else:
                log.warning(f"⚠️ Model pricing update failed, using cached/fallback data")
            
            return pricing_result
            
        except Exception as e:
            log.error(f"❌ Failed to update model pricing: {e}")
            return {
                "success": False,
                "error": str(e),
                "fetched_at": datetime.now().isoformat()
            }
    
    async def _consolidate_daily_usage(self, processing_date: date) -> Dict[str, Any]:
        """
        Validate and correct daily usage data for the given date
        Ensures markup costs are calculated correctly for all records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all client organizations
            cursor.execute("SELECT id, name, markup_rate FROM client_organizations WHERE is_active = 1")
            clients = cursor.fetchall()
            
            consolidation_stats = {
                "processing_date": processing_date.isoformat(),
                "clients_processed": 0,
                "total_records_verified": 0,
                "data_corrections": 0,
                "clients_data": []
            }
            
            for client_id, client_name, markup_rate in clients:
                # Validate and correct existing records
                # Get daily usage for this client and date
                cursor.execute("""
                    SELECT total_tokens, total_requests, raw_cost, markup_cost, primary_model
                    FROM client_daily_usage 
                    WHERE client_org_id = ? AND usage_date = ?
                """, (client_id, processing_date))
                
                daily_data = cursor.fetchone()
                
                if daily_data:
                    tokens, requests, raw_cost, markup_cost, primary_model = daily_data
                    
                    # Validate markup cost calculation
                    expected_markup_cost = raw_cost * markup_rate
                    cost_diff = abs(markup_cost - expected_markup_cost)
                    
                    client_stats = {
                        "client_id": client_id,
                        "client_name": client_name,
                        "tokens": tokens,
                        "requests": requests,
                        "raw_cost": raw_cost,
                        "markup_cost": markup_cost,
                        "markup_rate": markup_rate,
                        "primary_model": primary_model,
                        "data_validated": True
                    }
                    
                    # Correct markup cost if there's a significant difference (> 0.001)
                    if cost_diff > 0.001:
                        cursor.execute("""
                            UPDATE client_daily_usage 
                            SET markup_cost = ?, updated_at = ?
                            WHERE client_org_id = ? AND usage_date = ?
                        """, (expected_markup_cost, int(time.time()), client_id, processing_date))
                        
                        client_stats["markup_cost_corrected"] = {
                            "old_value": markup_cost,
                            "new_value": expected_markup_cost,
                            "difference": cost_diff
                        }
                        consolidation_stats["data_corrections"] += 1
                        
                        log.info(f"💰 Corrected markup cost for {client_name}: ${markup_cost:.6f} → ${expected_markup_cost:.6f}")
                    
                    consolidation_stats["clients_data"].append(client_stats)
                    consolidation_stats["total_records_verified"] += 1
                
                consolidation_stats["clients_processed"] += 1
            
            conn.commit()
            conn.close()
            
            log.info(f"📊 Daily consolidation completed: {consolidation_stats['clients_processed']} clients, "
                    f"{consolidation_stats['total_records_verified']} records verified, "
                    f"{consolidation_stats['data_corrections']} corrections made")
            
            return {
                "success": True,
                **consolidation_stats
            }
            
        except Exception as e:
            log.error(f"❌ Daily consolidation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_date": processing_date.isoformat()
            }
    
    async def _update_monthly_totals(self, current_date: date) -> Dict[str, Any]:
        """
        Update cumulative monthly totals from 1st day to current day
        Provides business-focused monthly overview data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current month boundaries
            month_start = current_date.replace(day=1)
            
            # Get all active clients
            cursor.execute("SELECT id, name FROM client_organizations WHERE is_active = 1")
            clients = cursor.fetchall()
            
            monthly_stats = {
                "processing_date": current_date.isoformat(),
                "month_range": f"{month_start.isoformat()} to {current_date.isoformat()}",
                "clients_processed": 0,
                "monthly_summaries": []
            }
            
            for client_id, client_name in clients:
                # Calculate monthly totals (1st to current day)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as days_with_usage,
                        SUM(total_tokens) as total_tokens,
                        SUM(total_requests) as total_requests,
                        SUM(raw_cost) as total_raw_cost,
                        SUM(markup_cost) as total_markup_cost,
                        AVG(total_tokens) as avg_daily_tokens,
                        MAX(total_tokens) as max_daily_tokens,
                        MAX(usage_date) as last_usage_date
                    FROM client_daily_usage 
                    WHERE client_org_id = ? 
                    AND usage_date >= ? 
                    AND usage_date <= ?
                """, (client_id, month_start, current_date))
                
                monthly_data = cursor.fetchone()
                
                if monthly_data and monthly_data[0] > 0:  # Has usage data
                    days_with_usage, total_tokens, total_requests, total_raw_cost, total_markup_cost, avg_daily, max_daily, last_usage = monthly_data
                    
                    # Calculate usage percentage
                    days_in_month = current_date.day
                    usage_percentage = (days_with_usage / days_in_month * 100) if days_in_month > 0 else 0
                    
                    # Get most used model
                    cursor.execute("""
                        SELECT primary_model, SUM(total_tokens) as model_tokens
                        FROM client_daily_usage 
                        WHERE client_org_id = ? 
                        AND usage_date >= ? 
                        AND usage_date <= ?
                        AND primary_model IS NOT NULL
                        GROUP BY primary_model
                        ORDER BY model_tokens DESC
                        LIMIT 1
                    """, (client_id, month_start, current_date))
                    
                    most_used_result = cursor.fetchone()
                    most_used_model = most_used_result[0] if most_used_result else None
                    
                    client_monthly_summary = {
                        "client_id": client_id,
                        "client_name": client_name,
                        "days_with_usage": days_with_usage,
                        "days_in_month": days_in_month,
                        "usage_percentage": round(usage_percentage, 1),
                        "total_tokens": total_tokens or 0,
                        "total_requests": total_requests or 0,
                        "total_raw_cost": total_raw_cost or 0.0,
                        "total_markup_cost": total_markup_cost or 0.0,
                        "average_daily_tokens": round(avg_daily or 0),
                        "max_daily_tokens": max_daily or 0,
                        "most_used_model": most_used_model,
                        "last_usage_date": last_usage
                    }
                    
                    monthly_stats["monthly_summaries"].append(client_monthly_summary)
                    
                    log.debug(f"📈 Monthly summary for {client_name}: {total_tokens:,} tokens, "
                             f"{days_with_usage}/{days_in_month} days ({usage_percentage:.1f}%)")
                
                monthly_stats["clients_processed"] += 1
            
            conn.close()
            
            # Calculate overall totals
            total_tokens_all = sum(s["total_tokens"] for s in monthly_stats["monthly_summaries"])
            total_cost_all = sum(s["total_markup_cost"] for s in monthly_stats["monthly_summaries"])
            
            log.info(f"📊 Monthly totals updated: {len(monthly_stats['monthly_summaries'])} active clients, "
                    f"{total_tokens_all:,} total tokens, ${total_cost_all:.6f} total cost")
            
            return {
                "success": True,
                **monthly_stats,
                "overall_totals": {
                    "total_tokens": total_tokens_all,
                    "total_markup_cost": total_cost_all,
                    "active_clients": len(monthly_stats["monthly_summaries"])
                }
            }
            
        except Exception as e:
            log.error(f"❌ Monthly totals update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_date": current_date.isoformat()
            }
    
    async def _cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up old processed generation records to prevent database bloat"""
        try:
            from open_webui.models.organization_usage import ProcessedGenerationDB
            
            # Clean up records older than 90 days
            cleanup_result = ProcessedGenerationDB.cleanup_old_processed_generations(days_to_keep=90)
            
            if cleanup_result["success"]:
                log.info(f"🧹 Data cleanup completed: {cleanup_result['records_deleted']} old records removed, "
                        f"~{cleanup_result['storage_saved_kb']}KB saved")
            
            return cleanup_result
            
        except Exception as e:
            log.error(f"❌ Data cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def run_daily_batch() -> Dict[str, Any]:
    """
    Entry point for daily batch processing
    Can be called from cron job or scheduler
    """
    processor = DailyBatchProcessor()
    return await processor.run_daily_batch()


if __name__ == "__main__":
    """
    Direct execution for testing or manual runs
    Usage: python daily_batch_processor.py
    """
    import sys
    
    print("🕰️ mAI Daily Batch Processor")
    print("=" * 40)
    print(f"Starting batch processing at {datetime.now().isoformat()}")
    
    try:
        result = asyncio.run(run_daily_batch())
        
        if result["success"]:
            print(f"✅ Batch processing completed successfully in {result['batch_duration_seconds']}s")
            print(f"📊 Operations completed: {len(result['operations'])}")
            
            for op in result["operations"]:
                status = "✅" if op["success"] else "❌"
                print(f"  {status} {op['operation']}")
        else:
            print(f"❌ Batch processing failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Batch processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)