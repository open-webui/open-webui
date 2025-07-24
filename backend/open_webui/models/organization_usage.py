import time
from typing import Optional, List
from datetime import datetime, date

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index
from sqlalchemy.orm import relationship


####################
# Organization Usage DB Schema
####################


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(String, primary_key=True)
    openrouter_org_id = Column(String, nullable=True)
    openrouter_api_key = Column(Text, nullable=True)
    sync_enabled = Column(Integer, default=1)  # Boolean as integer
    sync_interval_hours = Column(Integer, default=1)
    last_sync_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class OpenRouterUserMapping(Base):
    __tablename__ = "openrouter_user_mapping"

    id = Column(String, primary_key=True)
    owui_user_id = Column(String, nullable=False)
    openrouter_user_id = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_owui_user_id', 'owui_user_id'),
        Index('idx_openrouter_user_id', 'openrouter_user_id'),
    )


class OrganizationUsage(Base):
    __tablename__ = "organization_usage"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # OWUI user ID
    openrouter_user_id = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    usage_date = Column(Date, nullable=False)
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    total_cost = Column(Float, default=0.0)
    request_count = Column(Integer, default=0)
    
    # Metadata from OpenRouter
    provider = Column(String, nullable=True)
    generation_time = Column(Float, nullable=True)  # Time taken for generation
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'usage_date'),
        Index('idx_model_date', 'model_name', 'usage_date'),
        Index('idx_openrouter_user_date', 'openrouter_user_id', 'usage_date'),
    )


####################
# Pydantic Models
####################


class OrganizationSettingsModel(BaseModel):
    id: str
    openrouter_org_id: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    sync_enabled: bool = True
    sync_interval_hours: int = 1
    last_sync_at: Optional[int] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class OpenRouterUserMappingModel(BaseModel):
    id: str
    owui_user_id: str
    openrouter_user_id: str
    is_active: bool = True
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class OrganizationUsageModel(BaseModel):
    id: str
    user_id: str
    openrouter_user_id: str
    model_name: str
    usage_date: date
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    provider: Optional[str] = None
    generation_time: Optional[float] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms and Responses
####################


class OrganizationSettingsForm(BaseModel):
    openrouter_org_id: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    sync_enabled: bool = True
    sync_interval_hours: int = 1


class UserMappingForm(BaseModel):
    owui_user_id: str
    openrouter_user_id: str


class UsageStatsResponse(BaseModel):
    total_tokens: int
    total_cost: float
    total_requests: int
    models_used: int
    date_range: str


class UserUsageResponse(BaseModel):
    user_id: str
    user_name: str
    total_tokens: int
    total_cost: float
    total_requests: int
    models: List[dict]


class ModelUsageResponse(BaseModel):
    model_name: str
    total_tokens: int
    total_cost: float
    total_requests: int
    users: List[dict]


class DailyUsageResponse(BaseModel):
    date: str
    total_tokens: int
    total_cost: float
    total_requests: int
    breakdown: List[dict]


####################
# Database Operations
####################


class OrganizationSettingsTable:
    def get_settings(self) -> Optional[OrganizationSettingsModel]:
        """Get organization settings (should be singleton)"""
        try:
            with get_db() as db:
                settings = db.query(OrganizationSettings).first()
                if settings:
                    return OrganizationSettingsModel.model_validate(settings)
                return None
        except Exception:
            return None

    def create_or_update_settings(
        self, settings_form: OrganizationSettingsForm
    ) -> Optional[OrganizationSettingsModel]:
        """Create or update organization settings"""
        try:
            with get_db() as db:
                existing = db.query(OrganizationSettings).first()
                current_time = int(time.time())
                
                if existing:
                    # Update existing
                    for key, value in settings_form.model_dump().items():
                        setattr(existing, key, value)
                    existing.updated_at = current_time
                    db.commit()
                    db.refresh(existing)
                    return OrganizationSettingsModel.model_validate(existing)
                else:
                    # Create new
                    settings_data = settings_form.model_dump()
                    settings_data.update({
                        "id": "default",
                        "created_at": current_time,
                        "updated_at": current_time
                    })
                    new_settings = OrganizationSettings(**settings_data)
                    db.add(new_settings)
                    db.commit()
                    db.refresh(new_settings)
                    return OrganizationSettingsModel.model_validate(new_settings)
        except Exception:
            return None

    def update_last_sync(self) -> bool:
        """Update the last sync timestamp"""
        try:
            with get_db() as db:
                settings = db.query(OrganizationSettings).first()
                if settings:
                    settings.last_sync_at = int(time.time())
                    settings.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False


class OpenRouterUserMappingTable:
    def create_mapping(
        self, mapping_form: UserMappingForm
    ) -> Optional[OpenRouterUserMappingModel]:
        """Create a new user mapping"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                mapping_data = mapping_form.model_dump()
                mapping_data.update({
                    "id": f"{mapping_form.owui_user_id}_{mapping_form.openrouter_user_id}",
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                new_mapping = OpenRouterUserMapping(**mapping_data)
                db.add(new_mapping)
                db.commit()
                db.refresh(new_mapping)
                return OpenRouterUserMappingModel.model_validate(new_mapping)
        except Exception:
            return None

    def get_mapping_by_owui_user_id(
        self, owui_user_id: str
    ) -> Optional[OpenRouterUserMappingModel]:
        """Get mapping by OWUI user ID"""
        try:
            with get_db() as db:
                mapping = db.query(OpenRouterUserMapping).filter_by(
                    owui_user_id=owui_user_id, is_active=1
                ).first()
                if mapping:
                    return OpenRouterUserMappingModel.model_validate(mapping)
                return None
        except Exception:
            return None

    def get_all_active_mappings(self) -> List[OpenRouterUserMappingModel]:
        """Get all active user mappings"""
        try:
            with get_db() as db:
                mappings = db.query(OpenRouterUserMapping).filter_by(is_active=1).all()
                return [OpenRouterUserMappingModel.model_validate(m) for m in mappings]
        except Exception:
            return []

    def deactivate_mapping(self, owui_user_id: str) -> bool:
        """Deactivate a user mapping"""
        try:
            with get_db() as db:
                mapping = db.query(OpenRouterUserMapping).filter_by(
                    owui_user_id=owui_user_id
                ).first()
                if mapping:
                    mapping.is_active = 0
                    mapping.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False


class OrganizationUsageTable:
    def record_usage(
        self,
        user_id: str,
        openrouter_user_id: str,
        model_name: str,
        usage_date: date,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        provider: Optional[str] = None,
        generation_time: Optional[float] = None
    ) -> Optional[OrganizationUsageModel]:
        """Record or update daily usage for a user/model combination"""
        try:
            with get_db() as db:
                # Check if record exists for this user/model/date
                existing = db.query(OrganizationUsage).filter_by(
                    user_id=user_id,
                    model_name=model_name,
                    usage_date=usage_date
                ).first()
                
                current_time = int(time.time())
                total_tokens = input_tokens + output_tokens
                
                if existing:
                    # Update existing record
                    existing.input_tokens += input_tokens
                    existing.output_tokens += output_tokens
                    existing.total_tokens += total_tokens
                    existing.total_cost += cost
                    existing.request_count += 1
                    existing.updated_at = current_time
                    if generation_time:
                        existing.generation_time = generation_time
                    db.commit()
                    db.refresh(existing)
                    return OrganizationUsageModel.model_validate(existing)
                else:
                    # Create new record
                    usage_data = {
                        "id": f"{user_id}_{model_name}_{usage_date.isoformat()}",
                        "user_id": user_id,
                        "openrouter_user_id": openrouter_user_id,
                        "model_name": model_name,
                        "usage_date": usage_date,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "total_cost": cost,
                        "request_count": 1,
                        "provider": provider,
                        "generation_time": generation_time,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                    
                    new_usage = OrganizationUsage(**usage_data)
                    db.add(new_usage)
                    db.commit()
                    db.refresh(new_usage)
                    return OrganizationUsageModel.model_validate(new_usage)
        except Exception:
            return None

    def get_usage_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[OrganizationUsageModel]:
        """Get usage records within date range"""
        try:
            with get_db() as db:
                usage_records = db.query(OrganizationUsage).filter(
                    OrganizationUsage.usage_date >= start_date,
                    OrganizationUsage.usage_date <= end_date
                ).all()
                return [OrganizationUsageModel.model_validate(record) for record in usage_records]
        except Exception:
            return []

    def get_usage_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> UsageStatsResponse:
        """Get aggregated usage statistics"""
        try:
            with get_db() as db:
                query = db.query(OrganizationUsage)
                
                if start_date:
                    query = query.filter(OrganizationUsage.usage_date >= start_date)
                if end_date:
                    query = query.filter(OrganizationUsage.usage_date <= end_date)
                
                records = query.all()
                
                total_tokens = sum(r.total_tokens for r in records)
                total_cost = sum(r.total_cost for r in records)
                total_requests = sum(r.request_count for r in records)
                models_used = len(set(r.model_name for r in records))
                
                date_range = "All time"
                if start_date and end_date:
                    date_range = f"{start_date} to {end_date}"
                elif start_date:
                    date_range = f"From {start_date}"
                elif end_date:
                    date_range = f"Until {end_date}"
                
                return UsageStatsResponse(
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    total_requests=total_requests,
                    models_used=models_used,
                    date_range=date_range
                )
        except Exception:
            return UsageStatsResponse(
                total_tokens=0,
                total_cost=0.0,
                total_requests=0,
                models_used=0,
                date_range="Error"
            )


# Singleton instances
OrganizationSettingsDB = OrganizationSettingsTable()
OpenRouterUserMappingDB = OpenRouterUserMappingTable()
OrganizationUsageDB = OrganizationUsageTable()