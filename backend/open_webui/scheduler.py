# scheduler.py
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from open_webui.config import (
    CHAT_LIFETIME_ENABLED,
    CHAT_LIFETIME_DAYS,
    CHAT_CLEANUP_PRESERVE_PINNED,
    CHAT_CLEANUP_PRESERVE_ARCHIVED,
)

log = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None
CLEANUP_JOB_ID = "chat_lifetime_cleanup"


def get_scheduler():
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
        scheduler.start()
        log.info("Chat lifetime scheduler started")
    return scheduler


async def automated_chat_cleanup():
    """
    Automated chat cleanup job that respects current configuration.
    This is called by the scheduler when chat lifetime is enabled.
    """
    try:
        # Import here to avoid circular imports
        from open_webui.routers.retrieval import cleanup_expired_chats

        # Get current configuration values
        enabled = CHAT_LIFETIME_ENABLED.value
        days = CHAT_LIFETIME_DAYS.value
        preserve_pinned = CHAT_CLEANUP_PRESERVE_PINNED.value
        preserve_archived = CHAT_CLEANUP_PRESERVE_ARCHIVED.value

        if not enabled:
            log.info("Chat lifetime is disabled - skipping automated cleanup")
            return

        log.info(
            f"Starting automated chat cleanup (age > {days} days, preserve_pinned={preserve_pinned}, preserve_archived={preserve_archived})"
        )

        result = await cleanup_expired_chats(
            max_age_days=days,
            preserve_pinned=preserve_pinned,
            preserve_archived=preserve_archived,
            force_cleanup_all=False,  # Always use age-based cleanup for automation
        )

        log.info(f"Automated chat cleanup completed: {result}")

    except Exception as e:
        log.error(f"Automated chat cleanup failed: {str(e)}")


def update_cleanup_schedule():
    """
    Update the cleanup schedule based on current configuration.
    This should be called whenever chat lifetime settings change.
    """
    try:
        scheduler_instance = get_scheduler()

        # Remove existing job if it exists
        if scheduler_instance.get_job(CLEANUP_JOB_ID):
            scheduler_instance.remove_job(CLEANUP_JOB_ID)
            log.info("Removed existing chat cleanup schedule")

        # Check if chat lifetime is enabled
        if CHAT_LIFETIME_ENABLED.value:
            # Schedule daily cleanup at 2 AM
            trigger = CronTrigger(hour=2, minute=0)
            scheduler_instance.add_job(
                automated_chat_cleanup,
                trigger=trigger,
                id=CLEANUP_JOB_ID,
                name="Automated Chat Lifetime Cleanup",
                replace_existing=True,
            )

            days = CHAT_LIFETIME_DAYS.value
            log.info(f"Scheduled daily chat cleanup at 2:00 AM (lifetime: {days} days)")
        else:
            log.info("Chat lifetime disabled - no automated cleanup scheduled")

    except Exception as e:
        log.error(f"Failed to update cleanup schedule: {str(e)}")


def start_chat_lifetime_scheduler():
    """
    Initialize the chat lifetime scheduler.
    This should be called once when the application starts.
    """
    try:
        log.info("Initializing chat lifetime scheduler...")
        get_scheduler()  # Initialize scheduler
        update_cleanup_schedule()  # Set up initial schedule
        log.info("Chat lifetime scheduler initialization complete")
    except Exception as e:
        log.error(f"Failed to start chat lifetime scheduler: {str(e)}")


def stop_chat_lifetime_scheduler():
    """
    Stop the chat lifetime scheduler.
    This should be called when the application shuts down.
    """
    global scheduler
    if scheduler:
        try:
            scheduler.shutdown()
            scheduler = None
            log.info("Chat lifetime scheduler stopped")
        except Exception as e:
            log.error(f"Error stopping scheduler: {str(e)}")


def get_schedule_info():
    """
    Get information about the current cleanup schedule.
    Returns dict with schedule status and next run time.
    """
    try:
        if not CHAT_LIFETIME_ENABLED.value:
            return {
                "enabled": False,
                "status": "Disabled",
                "next_run": None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
            }

        scheduler_instance = get_scheduler()
        job = scheduler_instance.get_job(CLEANUP_JOB_ID)

        if job:
            next_run = job.next_run_time
            return {
                "enabled": True,
                "status": "Scheduled",
                "next_run": next_run.isoformat() if next_run else None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "schedule": "Daily at 2:00 AM",
            }
        else:
            return {
                "enabled": True,
                "status": "Error",
                "next_run": None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "error": "Job not found in scheduler",
            }

    except Exception as e:
        return {
            "enabled": CHAT_LIFETIME_ENABLED.value,
            "status": "Error",
            "next_run": None,
            "lifetime_days": CHAT_LIFETIME_DAYS.value,
            "error": str(e),
        }
