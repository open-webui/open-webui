"""
Enhanced Batch Scheduler with InfluxDB Support
Handles automated scheduling with choice between SQLite and InfluxDB processors
"""

import os
import asyncio
import logging
from datetime import datetime, date, time
from typing import Optional, Dict, Any
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)


class EnhancedBatchScheduler:
    """Enhanced scheduler supporting both SQLite and InfluxDB batch processing"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.influxdb_enabled = os.getenv("INFLUXDB_ENABLED", "false").lower() == "true"
        self.batch_processor_mode = os.getenv("BATCH_PROCESSOR_MODE", "auto")  # auto, sqlite, influxdb
        
    async def start(self):
        """Start the enhanced batch scheduler"""
        if self.is_running:
            log.warning("Batch scheduler already running")
            return
            
        try:
            # Create scheduler with CET timezone
            cet_tz = pytz.timezone('Europe/Warsaw')
            self.scheduler = AsyncIOScheduler(timezone=cet_tz)
            
            # Schedule daily batch processing at 13:00 CET/CEST
            self.scheduler.add_job(
                func=self._run_batch_with_processor_selection,
                trigger=CronTrigger(hour=13, minute=0, timezone=cet_tz),
                id='daily_batch_processing',
                name='Daily Batch Processing',
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600
            )
            
            # If dual-write mode is enabled, schedule validation
            if os.getenv("DUAL_WRITE_MODE", "false").lower() == "true":
                self.scheduler.add_job(
                    func=self._run_data_validation,
                    trigger=CronTrigger(hour=14, minute=0, timezone=cet_tz),  # 1 hour after batch
                    id='daily_data_validation',
                    name='Daily Data Validation',
                    replace_existing=True,
                    max_instances=1
                )
            
            self.scheduler.start()
            self.is_running = True
            
            next_run = self.scheduler.get_job('daily_batch_processing').next_run_time
            log.info(
                f"✅ Enhanced batch scheduler started - mode: {self._get_processor_mode()}, "
                f"next run: {next_run}"
            )
            
        except Exception as e:
            log.error(f"Failed to start enhanced batch scheduler: {e}")
            raise
    
    def _get_processor_mode(self) -> str:
        """Determine which batch processor to use"""
        if self.batch_processor_mode == "influxdb":
            return "influxdb"
        elif self.batch_processor_mode == "sqlite":
            return "sqlite"
        else:  # auto mode
            return "influxdb" if self.influxdb_enabled else "sqlite"
    
    async def _run_batch_with_processor_selection(self):
        """Run batch processing with automatic processor selection"""
        processor_mode = self._get_processor_mode()
        
        try:
            log.info(f"🕐 Starting scheduled batch processing using {processor_mode.upper()} processor")
            
            if processor_mode == "influxdb":
                result = await self._run_influxdb_batch()
            else:
                result = await self._run_sqlite_batch()
            
            self._log_batch_result(result, processor_mode)
            
        except Exception as e:
            log.error(f"❌ Critical error in scheduled batch processing ({processor_mode}): {e}")
    
    async def _run_sqlite_batch(self) -> Dict[str, Any]:
        """Run traditional SQLite-based batch processing"""
        from open_webui.utils.daily_batch_processor import run_daily_batch
        return await run_daily_batch()
    
    async def _run_influxdb_batch(self) -> Dict[str, Any]:
        """Run InfluxDB-based batch processing"""
        from open_webui.utils.daily_batch_processor_influx import run_influxdb_batch
        
        # Convert result to match expected format
        result = await run_influxdb_batch()
        
        # Transform InfluxDB result to match SQLite format
        if result.get("success"):
            return {
                "success": True,
                "operations": [
                    {
                        "success": True,
                        "operation": "influxdb_batch_processing",
                        "details": result
                    }
                ],
                "batch_duration_seconds": result.get("duration_seconds", 0),
                "processing_date": result.get("processing_date"),
                "completed_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "operations": []
            }
    
    async def _run_data_validation(self):
        """Run data validation between SQLite and InfluxDB"""
        try:
            log.info("🔍 Starting scheduled data validation")
            
            from open_webui.utils.influxdb_sqlite_comparison import DataConsistencyValidator
            
            validator = DataConsistencyValidator()
            yesterday = date.today() - timedelta(days=1)
            
            report = await validator.run_comprehensive_validation(
                yesterday, yesterday
            )
            
            if report["summary"]["total_discrepancies"] > 0:
                log.warning(
                    f"⚠️ Data validation found {report['summary']['total_discrepancies']} "
                    f"discrepancies for {yesterday}"
                )
            else:
                log.info(f"✅ Data validation successful - no discrepancies found for {yesterday}")
            
        except Exception as e:
            log.error(f"❌ Data validation failed: {e}")
    
    def _log_batch_result(self, result: Dict[str, Any], processor_mode: str):
        """Log batch processing results"""
        if result.get('success', False):
            if processor_mode == "influxdb":
                details = result.get('operations', [{}])[0].get('details', {})
                log.info(
                    f"✅ InfluxDB batch completed: "
                    f"{details.get('clients_processed', 0)} clients, "
                    f"{details.get('total_records', 0)} records, "
                    f"${details.get('total_cost_usd', 0):.2f} USD"
                )
            else:
                operations = result.get('operations', [])
                successful_ops = sum(1 for op in operations if op.get('success', False))
                total_ops = len(operations)
                duration = result.get('batch_duration_seconds', 0)
                log.info(
                    f"✅ SQLite batch completed: "
                    f"{successful_ops}/{total_ops} operations in {duration:.2f}s"
                )
        else:
            error = result.get('error', 'Unknown error')
            log.error(f"❌ Batch processing failed ({processor_mode}): {error}")
    
    async def stop(self):
        """Stop the enhanced batch scheduler"""
        if not self.is_running or not self.scheduler:
            return
            
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            log.info("✅ Enhanced batch scheduler stopped")
        except Exception as e:
            log.error(f"Error stopping enhanced batch scheduler: {e}")
        finally:
            self.scheduler = None
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        if not self.scheduler or not self.is_running:
            return None
            
        job = self.scheduler.get_job('daily_batch_processing')
        return job.next_run_time if job else None
    
    def is_scheduler_running(self) -> bool:
        """Check if scheduler is running"""
        return self.is_running and self.scheduler is not None


# Global scheduler instance
_enhanced_scheduler: Optional[EnhancedBatchScheduler] = None


async def init_enhanced_batch_scheduler():
    """Initialize enhanced batch scheduler on application startup"""
    global _enhanced_scheduler
    
    if _enhanced_scheduler is None:
        _enhanced_scheduler = EnhancedBatchScheduler()
    
    try:
        await _enhanced_scheduler.start()
        mode = _enhanced_scheduler._get_processor_mode()
        log.info(f"✅ Enhanced batch scheduler initialized for 13:00 CET/CEST (mode: {mode})")
    except Exception as e:
        log.error(f"Failed to initialize enhanced batch scheduler: {e}")


async def shutdown_enhanced_batch_scheduler():
    """Shutdown enhanced batch scheduler on application teardown"""
    global _enhanced_scheduler
    
    if _enhanced_scheduler:
        try:
            await _enhanced_scheduler.stop()
            log.info("✅ Enhanced batch scheduler shutdown successfully")
        except Exception as e:
            log.error(f"Failed to shutdown enhanced batch scheduler: {e}")
        finally:
            _enhanced_scheduler = None


def get_enhanced_batch_scheduler() -> Optional[EnhancedBatchScheduler]:
    """Get the global enhanced batch scheduler instance"""
    return _enhanced_scheduler


async def trigger_batch_manually(use_influxdb: Optional[bool] = None):
    """
    Manually trigger batch processing
    
    Args:
        use_influxdb: Force specific processor (None = auto-detect)
    """
    try:
        if use_influxdb is None:
            # Auto-detect based on configuration
            influxdb_enabled = os.getenv("INFLUXDB_ENABLED", "false").lower() == "true"
            use_influxdb = influxdb_enabled
        
        processor_type = "InfluxDB" if use_influxdb else "SQLite"
        log.info(f"🔧 Manual batch processing trigger initiated ({processor_type})")
        
        if use_influxdb:
            from open_webui.utils.daily_batch_processor_influx import run_influxdb_batch
            result = await run_influxdb_batch()
        else:
            from open_webui.utils.daily_batch_processor import run_daily_batch
            result = await run_daily_batch()
        
        log.info(f"✅ Manual batch processing completed ({processor_type})")
        return result
        
    except Exception as e:
        log.error(f"❌ Manual batch processing failed: {e}")
        raise


async def trigger_validation_manually(days_back: int = 1):
    """
    Manually trigger data validation
    
    Args:
        days_back: Number of days to validate
    """
    try:
        log.info(f"🔧 Manual data validation trigger initiated (last {days_back} days)")
        
        from open_webui.utils.influxdb_sqlite_comparison import DataConsistencyValidator
        
        validator = DataConsistencyValidator()
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days_back - 1)
        
        report = await validator.run_comprehensive_validation(start_date, end_date)
        
        log.info(f"✅ Manual data validation completed")
        return report
        
    except Exception as e:
        log.error(f"❌ Manual data validation failed: {e}")
        raise