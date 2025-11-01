"""
N8N Configuration and Execution Tracking Models

Manages N8N workflow configurations and execution history.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Integer, Boolean, JSON, Text, BigInteger
from sqlalchemy.sql import func
import time
import uuid
import re

from open_webui.internal.db import Base, get_db


####################
# DB Models
####################


class N8NConfig(Base):
    """N8N workflow configuration"""
    __tablename__ = "n8n_config"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    n8n_url = Column(String, nullable=False)
    webhook_id = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_streaming = Column(Boolean, default=True)
    timeout_seconds = Column(Integer, default=120)
    retry_config = Column(JSON, default={"max_retries": 3, "backoff": 2})
    metadata = Column(JSON, default={})
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class N8NWorkflowExecution(Base):
    """N8N workflow execution tracking"""
    __tablename__ = "n8n_executions"

    id = Column(String, primary_key=True)
    config_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # pending, success, failed, timeout
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, default={})
    created_at = Column(BigInteger, nullable=False)


####################
# Pydantic Schemas
####################


class N8NConfigForm(BaseModel):
    """N8N configuration form"""
    name: str
    n8n_url: str
    webhook_id: str
    api_key: Optional[str] = None
    is_active: bool = True
    is_streaming: bool = True
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    retry_config: dict = {"max_retries": 3, "backoff": 2}
    metadata: dict = {}

    @validator("n8n_url")
    def validate_url(cls, v):
        """Validate N8N URL format"""
        if not v:
            raise ValueError("N8N URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("N8N URL must start with http:// or https://")
        return v.rstrip("/")

    @validator("webhook_id")
    def validate_webhook_id(cls, v):
        """Validate webhook ID format"""
        if not v:
            raise ValueError("Webhook ID is required")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Webhook ID must contain only alphanumeric characters, hyphens, and underscores")
        return v


class N8NConfigModel(BaseModel):
    """N8N configuration model"""
    id: str
    user_id: str
    name: str
    n8n_url: str
    webhook_id: str
    api_key: Optional[str] = None
    is_active: bool
    is_streaming: bool
    timeout_seconds: int
    retry_config: dict
    metadata: dict
    created_at: int
    updated_at: int


class N8NExecutionForm(BaseModel):
    """N8N execution form"""
    prompt: Optional[str] = None
    data: dict = {}


class N8NExecutionModel(BaseModel):
    """N8N execution model"""
    id: str
    config_id: str
    user_id: str
    prompt: Optional[str]
    response: Optional[str]
    status: str
    duration_ms: Optional[int]
    error_message: Optional[str]
    metadata: dict
    created_at: int


####################
# Database Operations
####################


class N8NConfigs:
    """N8N Configuration database operations"""

    @staticmethod
    def create(form_data: N8NConfigForm, user_id: str) -> N8NConfigModel:
        """Create new N8N configuration"""
        with get_db() as db:
            timestamp = int(time.time())
            config = N8NConfig(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.dict(),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            db.add(config)
            db.commit()
            db.refresh(config)
            return N8NConfigModel(**{k: v for k, v in config.__dict__.items() if k[0] != "_"})

    @staticmethod
    def get_by_id(config_id: str) -> Optional[N8NConfigModel]:
        """Get configuration by ID"""
        with get_db() as db:
            config = db.query(N8NConfig).filter(N8NConfig.id == config_id).first()
            if config:
                return N8NConfigModel(**{k: v for k, v in config.__dict__.items() if k[0] != "_"})
            return None

    @staticmethod
    def get_by_user_id(user_id: str) -> list[N8NConfigModel]:
        """Get all configurations for a user"""
        with get_db() as db:
            configs = db.query(N8NConfig).filter(N8NConfig.user_id == user_id).all()
            return [N8NConfigModel(**{k: v for k, v in c.__dict__.items() if k[0] != "_"}) for c in configs]

    @staticmethod
    def update(config_id: str, form_data: N8NConfigForm) -> Optional[N8NConfigModel]:
        """Update configuration"""
        with get_db() as db:
            config = db.query(N8NConfig).filter(N8NConfig.id == config_id).first()
            if config:
                for key, value in form_data.dict(exclude_unset=True).items():
                    setattr(config, key, value)
                config.updated_at = int(time.time())
                db.commit()
                db.refresh(config)
                return N8NConfigModel(**{k: v for k, v in config.__dict__.items() if k[0] != "_"})
            return None

    @staticmethod
    def delete(config_id: str) -> bool:
        """Delete configuration"""
        with get_db() as db:
            config = db.query(N8NConfig).filter(N8NConfig.id == config_id).first()
            if config:
                db.delete(config)
                db.commit()
                return True
            return False


class N8NExecutions:
    """N8N Execution database operations"""

    @staticmethod
    def create(
        config_id: str,
        user_id: str,
        status: str,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: dict = {}
    ) -> N8NExecutionModel:
        """Create execution record"""
        with get_db() as db:
            execution = N8NWorkflowExecution(
                id=str(uuid.uuid4()),
                config_id=config_id,
                user_id=user_id,
                prompt=prompt,
                response=response,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                metadata=metadata,
                created_at=int(time.time())
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            return N8NExecutionModel(**{k: v for k, v in execution.__dict__.items() if k[0] != "_"})

    @staticmethod
    def get_by_config_id(config_id: str, limit: int = 100) -> list[N8NExecutionModel]:
        """Get executions for a configuration"""
        with get_db() as db:
            executions = (
                db.query(N8NWorkflowExecution)
                .filter(N8NWorkflowExecution.config_id == config_id)
                .order_by(N8NWorkflowExecution.created_at.desc())
                .limit(limit)
                .all()
            )
            return [N8NExecutionModel(**{k: v for k, v in e.__dict__.items() if k[0] != "_"}) for e in executions]

    @staticmethod
    def get_analytics(config_id: str) -> dict:
        """Get execution analytics for a configuration"""
        with get_db() as db:
            executions = db.query(N8NWorkflowExecution).filter(
                N8NWorkflowExecution.config_id == config_id
            ).all()

            if not executions:
                return {
                    "total_executions": 0,
                    "success_rate": 0,
                    "average_duration_ms": 0,
                    "status_breakdown": {}
                }

            total = len(executions)
            successful = sum(1 for e in executions if e.status == "success")
            durations = [e.duration_ms for e in executions if e.duration_ms is not None]

            status_counts = {}
            for e in executions:
                status_counts[e.status] = status_counts.get(e.status, 0) + 1

            return {
                "total_executions": total,
                "success_rate": successful / total if total > 0 else 0,
                "average_duration_ms": sum(durations) / len(durations) if durations else 0,
                "status_breakdown": status_counts
            }
