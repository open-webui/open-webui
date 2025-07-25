import time
import logging
from typing import Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Float

log = logging.getLogger(__name__)


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(String, primary_key=True)
    openrouter_provisioning_key = Column(Text, nullable=True)  # For creating client API keys
    default_markup_rate = Column(Float, default=1.3)
    billing_currency = Column(String, default="USD")
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GlobalSettingsModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    openrouter_provisioning_key: Optional[str] = None
    default_markup_rate: float = 1.3
    billing_currency: str = "USD"
    created_at: int
    updated_at: int


class GlobalSettingsForm(BaseModel):
    openrouter_provisioning_key: Optional[str] = None
    default_markup_rate: Optional[float] = None
    billing_currency: Optional[str] = None


class GlobalSettingsTable:
    """Service class for GlobalSettings operations"""
    
    def get_settings(self) -> Optional[GlobalSettingsModel]:
        with get_db() as db:
            settings = db.query(GlobalSettings).first()
            return GlobalSettingsModel.from_orm(settings) if settings else None

    def create_settings(self, form_data: GlobalSettingsForm) -> GlobalSettingsModel:
        with get_db() as db:
            settings = GlobalSettings(
                id="global",
                **form_data.dict(exclude_unset=True),
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
            return GlobalSettingsModel.from_orm(settings)

    def update_settings(self, form_data: GlobalSettingsForm) -> Optional[GlobalSettingsModel]:
        with get_db() as db:
            settings = db.query(GlobalSettings).first()
            if not settings:
                return self.create_settings(form_data)
            
            for key, value in form_data.dict(exclude_unset=True).items():
                setattr(settings, key, value)
            settings.updated_at = int(time.time())
            
            db.commit()
            db.refresh(settings)
            return GlobalSettingsModel.from_orm(settings)