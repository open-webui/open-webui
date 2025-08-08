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
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

class TokenUsage(Base):
    __tablename__ = "token_usage"

    group_name = Column(Text, unique=True, primary_key=True)
    token_in = Column(BigInteger, default=0)
    token_out = Column(BigInteger, default=0)
    token_total = Column(BigInteger, default=0)
    updated_at = Column(BigInteger)

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

    def create_token_group(self, name: str, models: List[str], limit: int) -> bool:
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
        """Update token usage for groups containing the model"""
        try:
            with get_db() as db:
                # Find groups containing this model
                groups = db.query(TokenGroup).all()
                
                for group in groups:
                    if model_id in group.models:
                        # Update usage for this group
                        usage = db.query(TokenUsage).filter_by(group_name=group.name).first()
                        if not usage:
                            usage = TokenUsage(
                                group_name=group.name,
                                token_in=token_in,
                                token_out=token_out,
                                token_total=token_total,
                                updated_at=int(time.time())
                            )
                            db.add(usage)
                        else:
                            usage.token_in += token_in
                            usage.token_out += token_out
                            usage.token_total += token_total
                            usage.updated_at = int(time.time())
                        
                        log.info(f"Updated usage for group {group.name}: +{token_in} IN, +{token_out} OUT, +{token_total} TOTAL")
                
                db.commit()
        except Exception as e:
            log.error(f"Error updating token usage for model {model_id}: {e}")

# Global instance
token_groups = TokenGroups()