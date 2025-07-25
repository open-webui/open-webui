import time
import logging
from typing import Optional, List
from datetime import datetime
import hashlib
import secrets

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Float, Integer, Index
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


class ClientOrganization(Base):
    __tablename__ = "client_organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    openrouter_api_key = Column(Text, nullable=False, unique=True)  # Dedicated key per client
    openrouter_key_hash = Column(String, nullable=True)  # OpenRouter's key identifier
    markup_rate = Column(Float, default=1.3)
    monthly_limit = Column(Float, nullable=True)  # Optional spending limit
    billing_email = Column(String, nullable=True)
    timezone = Column(String, default="Europe/Warsaw")  # Client's local timezone for accurate date calculations
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_api_key', 'openrouter_api_key'),
        Index('idx_active', 'is_active'),
    )


class UserClientMapping(Base):
    __tablename__ = "user_client_mapping"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # Open WebUI user ID
    client_org_id = Column(String, nullable=False)  # References client_organizations.id
    openrouter_user_id = Column(String, nullable=False)  # For OpenRouter user parameter
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_client_org_id', 'client_org_id'),
        Index('idx_openrouter_user_id', 'openrouter_user_id'),
    )


# Pydantic Models
class ClientOrganizationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    openrouter_api_key: str
    openrouter_key_hash: Optional[str] = None
    markup_rate: float = 1.3
    monthly_limit: Optional[float] = None
    billing_email: Optional[str] = None
    timezone: str = "Europe/Warsaw"
    is_active: bool = True
    created_at: int
    updated_at: int


class UserClientMappingModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    client_org_id: str
    openrouter_user_id: str
    is_active: bool = True
    created_at: int
    updated_at: int


class ClientOrganizationForm(BaseModel):
    name: str
    openrouter_api_key: str
    markup_rate: Optional[float] = 1.3
    monthly_limit: Optional[float] = None
    billing_email: Optional[str] = None
    timezone: Optional[str] = "Europe/Warsaw"


class UserClientMappingForm(BaseModel):
    user_id: str
    client_org_id: str
    openrouter_user_id: Optional[str] = None  # Auto-generated if not provided


# Service Classes
class ClientOrganizationTable:
    """Service class for ClientOrganization operations"""
    
    def get_by_id(self, client_id: str) -> Optional[ClientOrganizationModel]:
        with get_db() as db:
            client = db.query(ClientOrganization).filter_by(id=client_id).first()
            return ClientOrganizationModel.from_orm(client) if client else None

    def get_by_api_key(self, api_key: str) -> Optional[ClientOrganizationModel]:
        with get_db() as db:
            client = db.query(ClientOrganization).filter_by(openrouter_api_key=api_key).first()
            return ClientOrganizationModel.from_orm(client) if client else None

    def get_all_active(self) -> List[ClientOrganizationModel]:
        with get_db() as db:
            clients = db.query(ClientOrganization).filter_by(is_active=1).all()
            return [ClientOrganizationModel.from_orm(c) for c in clients]

    def create(self, form_data: ClientOrganizationForm) -> ClientOrganizationModel:
        client_id = f"org_{secrets.token_urlsafe(8)}"
        
        with get_db() as db:
            client = ClientOrganization(
                id=client_id,
                **form_data.dict(),
                is_active=1,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            
            # Generate key hash for tracking
            if form_data.openrouter_api_key:
                client.openrouter_key_hash = hashlib.sha256(
                    form_data.openrouter_api_key.encode()
                ).hexdigest()[:16]
            
            db.add(client)
            db.commit()
            db.refresh(client)
            return ClientOrganizationModel.from_orm(client)

    def update(self, client_id: str, form_data: ClientOrganizationForm) -> Optional[ClientOrganizationModel]:
        with get_db() as db:
            client = db.query(ClientOrganization).filter_by(id=client_id).first()
            if not client:
                return None
            
            for key, value in form_data.dict(exclude_unset=True).items():
                setattr(client, key, value)
            
            # Update key hash if API key changed
            if 'openrouter_api_key' in form_data.dict(exclude_unset=True):
                client.openrouter_key_hash = hashlib.sha256(
                    form_data.openrouter_api_key.encode()
                ).hexdigest()[:16]
            
            client.updated_at = int(time.time())
            
            db.commit()
            db.refresh(client)
            return ClientOrganizationModel.from_orm(client)

    def deactivate(self, client_id: str) -> bool:
        with get_db() as db:
            client = db.query(ClientOrganization).filter_by(id=client_id).first()
            if not client:
                return False
            
            client.is_active = 0
            client.updated_at = int(time.time())
            
            db.commit()
            return True


class UserClientMappingTable:
    """Service class for UserClientMapping operations"""
    
    def get_user_mapping(self, user_id: str) -> Optional[UserClientMappingModel]:
        with get_db() as db:
            mapping = db.query(UserClientMapping).filter_by(
                user_id=user_id, 
                is_active=1
            ).first()
            return UserClientMappingModel.from_orm(mapping) if mapping else None

    def get_client_users(self, client_org_id: str) -> List[UserClientMappingModel]:
        with get_db() as db:
            mappings = db.query(UserClientMapping).filter_by(
                client_org_id=client_org_id,
                is_active=1
            ).all()
            return [UserClientMappingModel.from_orm(m) for m in mappings]

    def create_mapping(self, form_data: UserClientMappingForm) -> UserClientMappingModel:
        mapping_id = f"map_{secrets.token_urlsafe(8)}"
        
        # Generate OpenRouter user ID if not provided
        if not form_data.openrouter_user_id:
            form_data.openrouter_user_id = f"user_{form_data.user_id[:8]}_{secrets.token_urlsafe(4)}"
        
        with get_db() as db:
            mapping = UserClientMapping(
                id=mapping_id,
                **form_data.dict(),
                is_active=1,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            
            db.add(mapping)
            db.commit()
            db.refresh(mapping)
            return UserClientMappingModel.from_orm(mapping)

    def update_mapping(self, user_id: str, client_org_id: str) -> Optional[UserClientMappingModel]:
        with get_db() as db:
            mapping = db.query(UserClientMapping).filter_by(
                user_id=user_id
            ).first()
            
            if not mapping:
                return None
            
            mapping.client_org_id = client_org_id
            mapping.updated_at = int(time.time())
            
            db.commit()
            db.refresh(mapping)
            return UserClientMappingModel.from_orm(mapping)

    def deactivate_mapping(self, user_id: str) -> bool:
        with get_db() as db:
            mapping = db.query(UserClientMapping).filter_by(user_id=user_id).first()
            if not mapping:
                return False
            
            mapping.is_active = 0
            mapping.updated_at = int(time.time())
            
            db.commit()
            return True