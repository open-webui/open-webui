import json
import logging
import time
from typing import Optional, Dict, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, func, Integer

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

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
    def get_token_groups(self) -> Dict:
        """Get all token groups with their usage data"""
        try:
            with get_db() as db:
                groups_query = db.query(TokenGroup).all()
                usage_query = db.query(TokenUsage).all()
                
                groups = {}
                usage_dict = {u.group_name: {
                    "in": u.token_in, 
                    "out": u.token_out, 
                    "total": u.token_total
                } for u in usage_query}
                
                for group in groups_query:
                    groups[group.name] = {
                        "models": group.models,
                        "limit": group.limit,
                        "usage": usage_dict.get(group.name, {"in": 0, "out": 0, "total": 0})
                    }
                    
                return groups
        except Exception as e:
            log.error(f"Error getting token groups: {e}")
            return {}

    def create_token_group(self, name: str, models: List[str], limit: int, reset_time: str = '00:00', reset_timezone: str = 'UTC') -> bool:
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

    def update_token_group(self, name: str, models: List[str] = None, limit: int = None) -> bool:
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
                                last_reset_date=current_date
                            )
                            db.add(usage)
                        else:
                            # Refresh the object from database to get latest column values
                            db.refresh(usage)
                            
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