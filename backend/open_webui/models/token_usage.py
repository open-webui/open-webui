import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, func, Integer, update

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def calculate_next_reset_timestamp(reset_time: str, reset_timezone: str) -> int:
    """
    Calculate the next reset timestamp based on reset_time (HH:MM) and timezone.
    Returns Unix timestamp of when the next reset should occur.
    """
    try:
        import pytz
    except ImportError:
        # Fallback to UTC if pytz not available
        reset_timezone = 'UTC'

    try:
        # Parse the reset time
        hour, minute = map(int, reset_time.split(':'))

        # Get current time in the specified timezone
        if reset_timezone == 'UTC':
            tz = timezone.utc
            now = datetime.now(tz)
        else:
            try:
                tz = pytz.timezone(reset_timezone)
                now = datetime.now(tz)
            except:
                tz = timezone.utc
                now = datetime.now(tz)

        # Calculate today's reset time in the timezone
        today_reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If we've already passed today's reset time, next reset is tomorrow
        if now >= today_reset:
            next_reset = today_reset + timedelta(days=1)
        else:
            next_reset = today_reset

        # Convert to UTC timestamp
        return int(next_reset.timestamp())
    except Exception as e:
        log.error(f"Error calculating next reset timestamp: {e}")
        # Default to midnight UTC next day
        now = datetime.now(timezone.utc)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return int(tomorrow.timestamp())


def calculate_rolling_window_next_reset(last_reset_timestamp: int, window_duration: int) -> int:
    """
    Calculate the next reset timestamp for rolling window strategy.
    Returns Unix timestamp of when the window expires.
    """
    if not last_reset_timestamp or not window_duration:
        return None
    return last_reset_timestamp + window_duration


def should_reset_daily(reset_time: str, reset_timezone: str, last_reset_date: str) -> bool:
    """
    Check if a daily reset should occur based on current time vs reset time.
    """
    try:
        import pytz
    except ImportError:
        reset_timezone = 'UTC'

    try:
        hour, minute = map(int, reset_time.split(':'))

        if reset_timezone == 'UTC':
            tz = timezone.utc
            now = datetime.now(tz)
        else:
            try:
                tz = pytz.timezone(reset_timezone)
                now = datetime.now(tz)
            except:
                tz = timezone.utc
                now = datetime.now(tz)

        current_date = now.strftime('%Y-%m-%d')
        today_reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If we've passed the reset time today but last_reset_date is not today
        # then we should reset
        if now >= today_reset and last_reset_date != current_date:
            return True

        # If last_reset_date is from a previous day (before yesterday), always reset
        if last_reset_date and last_reset_date < current_date:
            # Check if we're past the reset time for today
            if now >= today_reset:
                return True

        return False
    except Exception as e:
        log.error(f"Error checking daily reset: {e}")
        return False

####################
# Token Usage DB Schema
####################

class TokenGroup(Base):
    __tablename__ = "token_group"

    name = Column(Text, unique=True, primary_key=True)
    models = Column(JSON)  # List of model names
    limit = Column(BigInteger)  # Token limit for this group
    reset_time = Column(Text, default='00:00')  # Reset time in HH:MM format
    reset_timezone = Column(Text, default='UTC')  # Timezone for reset
    window_duration = Column(BigInteger, nullable=True)  # Rolling window duration in seconds
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

class TokenUsage(Base):
    __tablename__ = "token_usage"

    group_name = Column(Text, unique=True, primary_key=True)
    token_in = Column(BigInteger, default=0)
    token_out = Column(BigInteger, default=0)
    token_total = Column(BigInteger, default=0)
    updated_at = Column(BigInteger)
    last_reset_date = Column(Text, nullable=True)  # YYYY-MM-DD format (legacy)
    last_reset_timestamp = Column(BigInteger, nullable=True)  # Unix timestamp for precise scheduling

####################
# Token Usage DB Functions
####################

class TokenGroups:
    def get_token_groups(self, apply_resets: bool = True) -> Dict:
        """
        Get all token groups with their usage data.

        If apply_resets is True, this will check if any resets are due
        and apply them before returning the data. This ensures that
        clients always see the correct reset state even if no messages
        have been sent since the reset time.

        Returns a dict with group info including:
        - models: list of model IDs in this group
        - limit: token limit
        - window_duration: rolling window in seconds (if applicable)
        - usage: {in, out, total}
        - next_reset_at: Unix timestamp of next reset (for frontend scheduling)
        - reset_type: 'daily' or 'rolling_window'
        """
        try:
            with get_db() as db:
                groups_query = db.query(TokenGroup).all()
                usage_query = db.query(TokenUsage).all()

                # Build usage dict with full info for potential reset checks
                usage_dict = {}
                for u in usage_query:
                    usage_dict[u.group_name] = {
                        "in": u.token_in,
                        "out": u.token_out,
                        "total": u.token_total,
                        "last_reset_date": u.last_reset_date,
                        "last_reset_timestamp": u.last_reset_timestamp
                    }

                groups = {}
                current_timestamp = int(time.time())

                for group in groups_query:
                    usage_data = usage_dict.get(group.name, {
                        "in": 0, "out": 0, "total": 0,
                        "last_reset_date": None,
                        "last_reset_timestamp": None
                    })

                    reset_type = 'rolling_window' if group.window_duration else 'daily'
                    next_reset_at = None
                    should_reset = False

                    if group.window_duration:
                        # Rolling window logic
                        last_reset_ts = usage_data.get("last_reset_timestamp")
                        if last_reset_ts:
                            next_reset_at = calculate_rolling_window_next_reset(
                                last_reset_ts, group.window_duration
                            )
                            # Check if window has expired
                            if apply_resets and current_timestamp > next_reset_at:
                                should_reset = True
                                # After reset, next_reset is from now
                                next_reset_at = current_timestamp + group.window_duration
                        else:
                            # No usage yet, next reset will be window_duration after first usage
                            next_reset_at = None
                    else:
                        # Daily reset logic
                        reset_time = group.reset_time or '00:00'
                        reset_timezone = group.reset_timezone or 'UTC'
                        last_reset_date = usage_data.get("last_reset_date")

                        next_reset_at = calculate_next_reset_timestamp(reset_time, reset_timezone)

                        # Check if reset is due
                        if apply_resets and should_reset_daily(reset_time, reset_timezone, last_reset_date):
                            should_reset = True

                    # Apply reset if needed - use row-level locking to prevent race conditions
                    if should_reset and apply_resets:
                        # Lock the row to prevent concurrent resets
                        usage_record = db.query(TokenUsage).filter_by(
                            group_name=group.name
                        ).with_for_update(nowait=False).first()

                        if usage_record:
                            # Re-check if reset is still needed after acquiring lock
                            # (another process may have already done the reset)
                            still_needs_reset = False
                            if group.window_duration:
                                if usage_record.last_reset_timestamp:
                                    window_expired = current_timestamp > (usage_record.last_reset_timestamp + group.window_duration)
                                    still_needs_reset = window_expired
                            else:
                                reset_time = group.reset_time or '00:00'
                                reset_timezone = group.reset_timezone or 'UTC'
                                still_needs_reset = should_reset_daily(
                                    reset_time, reset_timezone, usage_record.last_reset_date
                                )

                            if still_needs_reset:
                                usage_record.token_in = 0
                                usage_record.token_out = 0
                                usage_record.token_total = 0
                                usage_record.updated_at = current_timestamp

                                if group.window_duration:
                                    usage_record.last_reset_timestamp = current_timestamp
                                    log.info(f"🔄 PROACTIVE RESET: Rolling window reset for group '{group.name}'")
                                else:
                                    now = datetime.now(timezone.utc)
                                    usage_record.last_reset_date = now.strftime('%Y-%m-%d')
                                    log.info(f"🔄 PROACTIVE RESET: Daily reset for group '{group.name}'")

                                db.commit()
                                # Update local data to reflect reset
                                usage_data = {"in": 0, "out": 0, "total": 0}
                            else:
                                # Another process already reset, just refresh our data
                                usage_data = {
                                    "in": usage_record.token_in,
                                    "out": usage_record.token_out,
                                    "total": usage_record.token_total
                                }
                                db.rollback()  # Release the lock without changes

                    groups[group.name] = {
                        "models": group.models,
                        "limit": group.limit,
                        "window_duration": group.window_duration,
                        "usage": {
                            "in": usage_data.get("in", 0),
                            "out": usage_data.get("out", 0),
                            "total": usage_data.get("total", 0)
                        },
                        "next_reset_at": next_reset_at,
                        "reset_type": reset_type
                    }

                return groups
        except Exception as e:
            log.error(f"Error getting token groups: {e}")
            return {}

    def create_token_group(self, name: str, models: List[str], limit: int, reset_time: str = '00:00', reset_timezone: str = 'UTC', window_duration: int = None) -> bool:
        """Create a new token group"""
        try:
            with get_db() as db:
                # Check if group already exists
                existing = db.query(TokenGroup).filter_by(name=name).first()
                if existing:
                    return False
                
                now = int(time.time())
                group = TokenGroup(
                    name=name,
                    models=models,
                    limit=limit,
                    reset_time=reset_time,
                    reset_timezone=reset_timezone,
                    window_duration=window_duration,
                    created_at=now,
                    updated_at=now
                )
                db.add(group)
                
                # Create usage entry
                usage = TokenUsage(
                    group_name=name,
                    token_in=0,
                    token_out=0,
                    token_total=0,
                    updated_at=now
                )
                db.add(usage)
                db.commit()
                
                log.info(f"Created token group: {name} with models {models} and limit {limit}")
                return True
        except Exception as e:
            log.error(f"Error creating token group {name}: {e}")
            return False

    def update_token_group(self, name: str, models: List[str] = None, limit: int = None, window_duration: int = None) -> bool:
        """Update an existing token group"""
        try:
            with get_db() as db:
                group = db.query(TokenGroup).filter_by(name=name).first()
                if not group:
                    return False
                
                if models is not None:
                    group.models = models
                if limit is not None:
                    group.limit = limit
                if window_duration is not None:
                    group.window_duration = window_duration
                group.updated_at = int(time.time())
                
                db.commit()
                log.info(f"Updated token group: {name}")
                return True
        except Exception as e:
            log.error(f"Error updating token group {name}: {e}")
            return False

    def delete_token_group(self, name: str) -> bool:
        """Delete a token group"""
        try:
            with get_db() as db:
                group = db.query(TokenGroup).filter_by(name=name).first()
                usage = db.query(TokenUsage).filter_by(group_name=name).first()
                
                if group:
                    db.delete(group)
                if usage:
                    db.delete(usage)
                    
                db.commit()
                log.info(f"Deleted token group: {name}")
                return True
        except Exception as e:
            log.error(f"Error deleting token group {name}: {e}")
            return False

    def update_token_usage(self, model_id: str, token_in: int, token_out: int, token_total: int):
        """Update token usage for groups containing the model (with daily reset check)"""
        from datetime import datetime, timezone
        from sqlalchemy import text
        
        try:
            current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            with get_db() as db:
                # Verify column exists in database (one-time check)
                try:
                    result = db.execute(text("PRAGMA table_info(token_usage)")).fetchall()
                    columns = [row[1] for row in result]  # Column names are in index 1
                    has_reset_column = 'last_reset_date' in columns
                    log.debug(f"🔄 RESET DEBUG: Database has last_reset_date column: {has_reset_column}")
                    if not has_reset_column:
                        log.warning("🔄 RESET DEBUG: last_reset_date column missing - migration may have failed")
                except Exception as e:
                    log.error(f"🔄 RESET DEBUG: Could not verify database schema: {e}")
                    has_reset_column = False
                # Find groups containing this model
                groups = db.query(TokenGroup).all()
                
                for group in groups:
                    if model_id in group.models:
                        # Get or create usage record
                        usage = db.query(TokenUsage).filter_by(group_name=group.name).first()
                        if not usage:
                            # First time usage - create with current date
                            usage = TokenUsage(
                                group_name=group.name,
                                token_in=token_in,
                                token_out=token_out,
                                token_total=token_total,
                                updated_at=int(time.time()),
                                last_reset_date=current_date,
                                last_reset_timestamp=int(time.time())
                            )
                            db.add(usage)
                        else:
                            # Refresh the object from database to get latest column values
                            db.refresh(usage)
                            
                            if group.window_duration:
                                # Rolling Window Reset Logic
                                current_timestamp = int(time.time())
                                last_reset_ts = usage.last_reset_timestamp
                                
                                if not last_reset_ts:
                                    # First usage in this mode, start the window
                                    usage.last_reset_timestamp = current_timestamp
                                    usage.token_in += token_in
                                    usage.token_out += token_out
                                    usage.token_total += token_total
                                    usage.updated_at = current_timestamp
                                    log.debug(f"🔄 WINDOW START: Group '{group.name}' started new window at {current_timestamp}")
                                elif current_timestamp > (last_reset_ts + group.window_duration):
                                    # Window expired, reset
                                    usage.token_in = token_in
                                    usage.token_out = token_out
                                    usage.token_total = token_total
                                    usage.last_reset_timestamp = current_timestamp
                                    usage.updated_at = current_timestamp
                                    log.info(f"🔄 WINDOW RESET: Reset tokens for group '{group.name}' (window expired)")
                                else:
                                    # Within window, accumulate
                                    usage.token_in += token_in
                                    usage.token_out += token_out
                                    usage.token_total += token_total
                                    usage.updated_at = current_timestamp
                                    log.debug(f"🔄 WINDOW UPDATE: Group '{group.name}' usage updated within window")
                                
                            else:
                                # Daily Reset Logic
                                # Check if daily reset is needed (handle missing attribute safely)
                                last_reset = getattr(usage, 'last_reset_date', None)
                                log.debug(f"🔄 RESET DEBUG: Group '{group.name}' last_reset='{last_reset}', current_date='{current_date}'")
                                
                                if last_reset != current_date:
                                    # Reset counters for new day (or first time with new column)
                                    usage.token_in = token_in  # Start fresh with current usage
                                    usage.token_out = token_out
                                    usage.token_total = token_total
                                    usage.last_reset_date = current_date
                                    usage.updated_at = int(time.time())
                                    
                                    reset_reason = "first run" if last_reset is None else "new day"
                                    log.info(f"🔄 DAILY RESET: Reset tokens for group '{group.name}' on {current_date} ({reset_reason})")
                                    log.debug(f"🔄 RESET DEBUG: Set last_reset_date to '{current_date}' for group '{group.name}'")
                                else:
                                    # Normal increment for same day
                                    usage.token_in += token_in
                                    usage.token_out += token_out
                                    usage.token_total += token_total
                                    usage.updated_at = int(time.time())
                                    log.debug(f"🔄 RESET DEBUG: Same day increment for group '{group.name}'")
                        
                        log.info(f"Updated usage for group {group.name}: +{token_in} IN, +{token_out} OUT, +{token_total} TOTAL")
                
                # Force flush and commit to ensure data is written
                db.flush()
                db.commit()
                log.debug(f"🔄 RESET DEBUG: Database committed for group '{group.name}'")
        except Exception as e:
            log.error(f"Error updating token usage for model {model_id}: {e}")

    def force_reset_all_usage(self):
        """Manually reset all token usage (for testing)"""
        from datetime import datetime, timezone
        
        try:
            current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            with get_db() as db:
                usage_records = db.query(TokenUsage).all()
                reset_count = 0
                
                for usage in usage_records:
                    usage.token_in = 0
                    usage.token_out = 0
                    usage.token_total = 0
                    usage.last_reset_date = current_date
                    usage.updated_at = int(time.time())
                    reset_count += 1
                
                db.commit()
                log.info(f"🔄 MANUAL RESET: Force reset {reset_count} token groups")
                return True
                
        except Exception as e:
            log.error(f"Error during manual token usage reset: {e}")
            return False

# Global instance
token_groups = TokenGroups()