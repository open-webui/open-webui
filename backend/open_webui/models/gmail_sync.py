"""
Gmail Sync Status Database Model

Tracks Gmail sync status for each user to enable incremental syncing.
Stores last sync timestamps, Gmail history IDs, and sync statistics.
"""

import time
import logging
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Boolean

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Gmail Sync DB Schema
####################


class GmailSyncStatus(Base):
    """Database model for tracking Gmail sync status per user"""

    __tablename__ = "gmail_sync_status"

    # Primary key - user ID
    user_id = Column(String, primary_key=True)

    # Sync tracking
    last_sync_timestamp = Column(BigInteger, nullable=True)  # Unix timestamp of last sync
    last_sync_history_id = Column(String, nullable=True)  # Gmail history ID for incremental sync
    last_sync_email_id = Column(String, nullable=True)  # Last processed email ID

    # Sync statistics
    total_emails_synced = Column(Integer, default=0)  # Total emails ever synced
    last_sync_count = Column(Integer, default=0)  # Emails synced in last run
    last_sync_duration = Column(Integer, default=0)  # Last sync duration in seconds

    # Sync status and configuration
    # Valid statuses: "never" (initial), "active" (sync in progress),
    # "completed" (sync finished successfully), "paused", "error"
    sync_status = Column(String, default="never")
    sync_enabled = Column(Boolean, default=True)  # Whether sync is enabled for user
    auto_sync_enabled = Column(Boolean, default=True)  # Whether to auto-sync on login

    # Error tracking
    last_error = Column(Text, nullable=True)  # Last error message
    error_count = Column(Integer, default=0)  # Number of consecutive errors

    # Sync preferences
    sync_frequency_hours = Column(Integer, default=24)  # How often to sync (hours)
    max_emails_per_sync = Column(Integer, default=100)  # Max emails per sync run

    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()))


class GmailSyncStatusModel(BaseModel):
    """Pydantic model for Gmail sync status"""

    user_id: str
    last_sync_timestamp: Optional[int] = None
    last_sync_history_id: Optional[str] = None
    last_sync_email_id: Optional[str] = None

    total_emails_synced: int = 0
    last_sync_count: int = 0
    last_sync_duration: int = 0

    sync_status: str = "never"  # "never", "active", "completed", "paused", "error"
    sync_enabled: bool = True
    auto_sync_enabled: bool = True

    last_error: Optional[str] = None
    error_count: int = 0

    sync_frequency_hours: int = 24
    max_emails_per_sync: int = 100

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Database Operations
####################


class GmailSyncStatusTable:
    """Database operations for Gmail sync status"""

    def get_sync_status(self, user_id: str) -> Optional[GmailSyncStatusModel]:
        """Get sync status for a user"""
        try:
            with get_db() as db:
                status = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                if status:
                    return GmailSyncStatusModel.model_validate(status)
                return None
        except Exception as e:
            log.error(f"Error getting sync status for user {user_id}: {e}")
            return None

    def create_sync_status(self, user_id: str) -> GmailSyncStatusModel:
        """Create initial sync status for a user"""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        try:
            with get_db() as db:
                # Check if already exists
                existing = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                if existing:
                    log.info(f"Sync status already exists for user {user_id}")
                    return GmailSyncStatusModel.model_validate(existing)

                # Create new status
                now = int(time.time())
                sync_status = GmailSyncStatus(user_id=user_id, created_at=now, updated_at=now)

                db.add(sync_status)
                db.commit()
                db.refresh(sync_status)

                log.info(f"Created new sync status for user {user_id}")
                return GmailSyncStatusModel.model_validate(sync_status)

        except Exception as e:
            log.error(f"Error creating sync status for user {user_id}: {e}")
            raise

    def update_sync_status(self, user_id: str, **updates) -> Optional[GmailSyncStatusModel]:
        """Update sync status for a user with transaction safety"""
        if not user_id or not isinstance(user_id, str):
            log.error(f"Invalid user_id: {user_id}")
            return None

        try:
            with get_db() as db:
                try:
                    status = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                    if not status:
                        log.warning(f"No sync status found for user {user_id}")
                        return None

                    # Validate updates
                    valid_fields = {
                        "last_sync_timestamp",
                        "last_sync_history_id",
                        "last_sync_email_id",
                        "total_emails_synced",
                        "last_sync_count",
                        "last_sync_duration",
                        "sync_status",
                        "sync_enabled",
                        "auto_sync_enabled",
                        "last_error",
                        "error_count",
                        "sync_frequency_hours",
                        "max_emails_per_sync",
                    }

                    # Update only valid fields
                    for key, value in updates.items():
                        if key in valid_fields and hasattr(status, key):
                            setattr(status, key, value)
                        else:
                            log.warning(f"Invalid field '{key}' for sync status update")

                    # Always update timestamp
                    status.updated_at = int(time.time())

                    db.commit()
                    db.refresh(status)

                    return GmailSyncStatusModel.model_validate(status)

                except Exception as e:
                    db.rollback()
                    log.error(f"Database error updating sync status for user {user_id}: {e}")
                    return None

        except Exception as e:
            log.error(f"Error updating sync status for user {user_id}: {e}")
            return None

    def mark_sync_start(self, user_id: str) -> Optional[GmailSyncStatusModel]:
        """Mark sync as starting"""
        return self.update_sync_status(
            user_id=user_id,
            sync_status="active",
            error_count=0,  # Reset error count on successful start
            last_error=None,
        )

    def mark_sync_complete(
        self,
        user_id: str,
        emails_synced: int,
        duration_seconds: int,
        last_history_id: Optional[str] = None,
        last_email_id: Optional[str] = None,
    ) -> Optional[GmailSyncStatusModel]:
        """Mark sync as completed successfully"""
        try:
            with get_db() as db:
                # Get current total first
                current_status = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                if not current_status:
                    log.error(f"No sync status found for user {user_id}")
                    return None

                new_total = current_status.total_emails_synced + emails_synced

                # Update with correct total
                # Set sync_status to "completed" so user can be picked up on next cycle
                # ("active" would cause user to be filtered out by get_users_needing_sync)
                return self.update_sync_status(
                    user_id=user_id,
                    sync_status="completed",
                    last_sync_timestamp=int(time.time()),
                    last_sync_history_id=last_history_id,
                    last_sync_email_id=last_email_id,
                    last_sync_count=emails_synced,
                    last_sync_duration=duration_seconds,
                    total_emails_synced=new_total,
                )
        except Exception as e:
            log.error(f"Error marking sync complete for user {user_id}: {e}")
            return None

    def mark_sync_error(self, user_id: str, error_message: str) -> Optional[GmailSyncStatusModel]:
        """Mark sync as failed with error"""
        try:
            with get_db() as db:
                # Get current error count first
                current_status = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                if not current_status:
                    log.error(f"No sync status found for user {user_id}")
                    return None

                new_error_count = current_status.error_count + 1

                return self.update_sync_status(
                    user_id=user_id,
                    sync_status="error",
                    last_error=error_message,
                    error_count=new_error_count,
                )
        except Exception as e:
            log.error(f"Error marking sync error for user {user_id}: {e}")
            return None

    def get_users_needing_sync(
        self,
        max_hours_since_sync: float = 24,
        stuck_sync_timeout_hours: float = 2.0,
    ) -> list[str]:
        """
        Get list of user IDs that need syncing (production-optimized).

        Performance features:
        - Uses indexed columns (sync_enabled, auto_sync_enabled, sync_status, last_sync_timestamp)
        - Selects only user_id (minimal data transfer)
        - Query benefits from composite index: gmail_sync_enabled_idx
        - Executes as single SELECT with WHERE clause
        - Auto-recovers stuck syncs that have been "active" too long

        Args:
            max_hours_since_sync: Hours since last sync to consider stale (can be fractional,
                                  e.g., 0.25 for 15 minutes)
            stuck_sync_timeout_hours: Hours after which an "active" sync is considered stuck
                                      and should be reset (default: 2 hours)

        Returns:
            list[str]: User IDs needing sync
        """
        try:
            with get_db() as db:
                cutoff_time = int(time.time() - (max_hours_since_sync * 3600))
                stuck_cutoff_time = int(time.time() - (stuck_sync_timeout_hours * 3600))

                # First, log total users with sync records for debugging
                total_sync_records = db.query(GmailSyncStatus).count()
                enabled_users = (
                    db.query(GmailSyncStatus)
                    .filter(
                        GmailSyncStatus.sync_enabled == True,
                        GmailSyncStatus.auto_sync_enabled == True,
                    )
                    .count()
                )

                log.debug(
                    f"Gmail sync status: {total_sync_records} total records, " f"{enabled_users} with sync+auto enabled"
                )

                # Check for stuck syncs first (sync_status == "active" but updated_at is old)
                stuck_syncs = (
                    db.query(GmailSyncStatus)
                    .filter(
                        GmailSyncStatus.sync_enabled == True,
                        GmailSyncStatus.auto_sync_enabled == True,
                        GmailSyncStatus.sync_status == "active",
                        GmailSyncStatus.updated_at < stuck_cutoff_time,
                    )
                    .all()
                )

                # Auto-reset stuck syncs
                stuck_user_ids = []
                for stuck in stuck_syncs:
                    stuck_duration_hours = (time.time() - stuck.updated_at) / 3600
                    log.warning(
                        f"⚠️  Resetting stuck sync for user {stuck.user_id} "
                        f"(stuck for {stuck_duration_hours:.1f} hours)"
                    )
                    stuck.sync_status = "error"
                    stuck.last_error = f"Sync timed out after {stuck_duration_hours:.1f} hours (auto-reset)"
                    stuck.updated_at = int(time.time())
                    stuck_user_ids.append(stuck.user_id)

                if stuck_syncs:
                    db.commit()
                    log.info(f"🔄 Auto-reset {len(stuck_syncs)} stuck sync(s)")

                # Optimized query - leverages database indexes
                # Index usage: gmail_sync_enabled_idx (sync_enabled, auto_sync_enabled)
                #              gmail_sync_last_sync_idx (last_sync_timestamp)
                #              gmail_sync_status_idx (sync_status)
                users = (
                    db.query(GmailSyncStatus.user_id)
                    .filter(
                        GmailSyncStatus.sync_enabled == True,
                        GmailSyncStatus.auto_sync_enabled == True,
                        GmailSyncStatus.sync_status != "active",  # Avoid double-sync
                        (
                            (GmailSyncStatus.last_sync_timestamp == None)  # Never synced
                            | (GmailSyncStatus.last_sync_timestamp < cutoff_time)  # Stale
                        ),
                    )
                    .all()
                )

                result = [user.user_id for user in users]

                if not result and enabled_users > 0:
                    # Debug: Check why enabled users aren't being picked up
                    active_users = (
                        db.query(GmailSyncStatus)
                        .filter(
                            GmailSyncStatus.sync_enabled == True,
                            GmailSyncStatus.auto_sync_enabled == True,
                            GmailSyncStatus.sync_status == "active",
                        )
                        .count()
                    )

                    recent_users = (
                        db.query(GmailSyncStatus)
                        .filter(
                            GmailSyncStatus.sync_enabled == True,
                            GmailSyncStatus.auto_sync_enabled == True,
                            GmailSyncStatus.last_sync_timestamp >= cutoff_time,
                        )
                        .count()
                    )

                    log.info(
                        f"📊 No users need sync: {active_users} currently syncing, "
                        f"{recent_users} synced recently (within {max_hours_since_sync:.2f}h)"
                    )

                return result

        except Exception as e:
            log.error(f"Error getting users needing sync: {e}")
            return []

    def delete_sync_status(self, user_id: str) -> bool:
        """Delete sync status for a user (when they disconnect Gmail)"""
        try:
            with get_db() as db:
                status = db.query(GmailSyncStatus).filter_by(user_id=user_id).first()
                if status:
                    db.delete(status)
                    db.commit()
                    return True
                return False

        except Exception as e:
            log.error(f"Error deleting sync status for user {user_id}: {e}")
            return False


# Global instance
gmail_sync_status = GmailSyncStatusTable()
