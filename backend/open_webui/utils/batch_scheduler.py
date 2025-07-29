"""
Daily Batch Processing Scheduler
Handles automated scheduling of daily batch processing at 13:00 CET/CEST
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

class BatchScheduler:
    """Scheduler for daily batch processing at 13:00 CET/CEST"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        
    async def start(self):
        """Start the batch scheduler"""
        if self.is_running:
            log.warning("Batch scheduler already running")
            return
            
        try:
            # Import here to avoid circular imports
            from open_webui.utils.daily_batch_processor import run_daily_batch
            
            # Create scheduler with CET timezone
            cet_tz = pytz.timezone('Europe/Warsaw')  # CET/CEST timezone
            self.scheduler = AsyncIOScheduler(timezone=cet_tz)
            
            # Schedule daily batch processing at 13:00 CET/CEST
            self.scheduler.add_job(
                func=self._run_batch_with_error_handling,
                trigger=CronTrigger(hour=13, minute=0, timezone=cet_tz),
                id='daily_batch_processing',
                name='Daily Batch Processing',
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
                coalesce=True,    # Combine missed runs
                misfire_grace_time=3600  # 1 hour grace period for missed runs
            )
            
            self.scheduler.start()
            self.is_running = True
            
            next_run = self.scheduler.get_job('daily_batch_processing').next_run_time
            log.info(f"✅ Daily batch scheduler started - next run: {next_run}")
            
        except Exception as e:
            log.error(f"Failed to start batch scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the batch scheduler"""
        if not self.is_running or not self.scheduler:
            return
            
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            log.info("✅ Daily batch scheduler stopped")
        except Exception as e:
            log.error(f"Error stopping batch scheduler: {e}")
        finally:
            self.scheduler = None
    
    async def _run_batch_with_error_handling(self):
        """Wrapper to handle batch processing with comprehensive error handling"""
        try:
            log.info("🕐 Starting scheduled daily batch processing at 13:00 CET")
            
            # Import here to avoid circular imports
            from open_webui.utils.daily_batch_processor import run_daily_batch
            
            result = await run_daily_batch()
            
            if result.get('success', False):
                operations = result.get('operations', [])
                successful_ops = sum(1 for op in operations if op.get('success', False))
                total_ops = len(operations)
                duration = result.get('batch_duration_seconds', 0)
                
                log.info(
                    f"✅ Scheduled batch processing completed successfully: "
                    f"{successful_ops}/{total_ops} operations in {duration:.2f}s"
                )
            else:
                error = result.get('error', 'Unknown error')
                log.error(f"❌ Scheduled batch processing failed: {error}")
                
        except Exception as e:
            log.error(f"❌ Critical error in scheduled batch processing: {e}")
            # In production, you might want to send alerts here
    
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
_batch_scheduler: Optional[BatchScheduler] = None

async def init_batch_scheduler():
    """Initialize batch scheduler on application startup"""
    global _batch_scheduler
    
    if _batch_scheduler is None:
        _batch_scheduler = BatchScheduler()
    
    try:
        await _batch_scheduler.start()
        log.info("✅ Daily batch scheduler initialized for 13:00 CET/CEST")
    except Exception as e:
        log.error(f"Failed to initialize batch scheduler: {e}")

async def shutdown_batch_scheduler():
    """Shutdown batch scheduler on application teardown"""
    global _batch_scheduler
    
    if _batch_scheduler:
        try:
            await _batch_scheduler.stop()
            log.info("✅ Daily batch scheduler shutdown successfully")
        except Exception as e:
            log.error(f"Failed to shutdown batch scheduler: {e}")
        finally:
            _batch_scheduler = None

def get_batch_scheduler() -> Optional[BatchScheduler]:
    """Get the global batch scheduler instance"""
    return _batch_scheduler

# Manual trigger function for testing/admin use
async def trigger_batch_manually():
    """Manually trigger batch processing (for testing or admin use)"""
    try:
        log.info("🔧 Manual batch processing trigger initiated")
        
        from open_webui.utils.daily_batch_processor import run_daily_batch
        result = await run_daily_batch()
        
        log.info("✅ Manual batch processing completed")
        return result
        
    except Exception as e:
        log.error(f"❌ Manual batch processing failed: {e}")
        raise