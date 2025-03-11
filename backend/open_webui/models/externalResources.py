import logging
from typing import Optional
from sqlalchemy import Column, String, Text, Enum, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict

# Initialize logging
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# ================================================================
# ExternalResource Database Schema
# ================================================================
class ExternalResource(Base):  
    __tablename__ = "external_resources"  # Change table name too
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)  
    resource_link = Column(String, nullable=False)  
    sync_enabled = Column(Boolean, default=True)
    sync_interval = Column(Integer, default=3600)
    page_token = Column(String, nullable=True)
    start_sync_token = Column(String, nullable=True)  # Token from startPageToken API

    last_synced_at = Column(DateTime, nullable=True)
    resource_created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Correct
    files = relationship("File", back_populates="external_resource", cascade="all, delete-orphan") 
    def __repr__(self):
        return f"<ExternalResource(id={self.id}, resource_link='{self.resource_link}')>"

# ================================================================
# Pydantic Model for Serialization and Validation
# ================================================================
class ExternalResourceModel(BaseModel):  # Renamed from GoogleDriveLinkModel
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int]
    user_id: str
    resource_link: str  # Renamed from drive_link to resource_link
    sync_enabled: Optional[bool] = True
    sync_interval: Optional[int] = 3600
    last_synced_at: Optional[datetime] = None
    page_token: Optional[str] = None
    resource_created_at: Optional[datetime] = None  # Updated field name

# ================================================================
# Database Operations for ExternalResource Table
# ================================================================
class ExternalResourcesTable:  # Renamed from GoogleDriveLinksTable
    def insert_new_resource(  # Renamed from insert_new_link
        self,
        user_id: str,
        resource_link: str,  # Renamed from drive_link
        page_token: Optional[str] = None
    ) -> Optional[ExternalResourceModel]:  # Updated to return ExternalResourceModel
        with get_db() as db:
            try:
                external_resource = ExternalResource(  # Updated class name
                    user_id=user_id,
                    resource_link=resource_link,  # Updated property name
                    page_token=page_token,
                    resource_created_at=datetime.utcnow()
                )
                db.add(external_resource)
                db.commit()
                db.refresh(external_resource)
                return ExternalResourceModel(**external_resource.__dict__)  # Updated Pydantic model
            except Exception as e:
                log.error(f"Error inserting external resource: {e}")
                return None

    def get_resource_by_id(self, resource_id: int) -> Optional[ExternalResourceModel]:  # Updated method name
        with get_db() as db:
            try:
                resource = db.query(ExternalResource).filter_by(id=resource_id).first()
                return ExternalResourceModel(**resource.__dict__) if resource else None
            except Exception as e:
                log.error(f"Error fetching external resource by ID {resource_id}: {e}")
                return None

    def update_last_sync_and_token(self, resource_id: int, page_token: Optional[str]) -> Optional[ExternalResourceModel]:
        with get_db() as db:
            try:
                resource = db.query(ExternalResource).filter_by(id=resource_id).first()
                if resource:
                    resource.last_synced_at = datetime.utcnow()
                    resource.page_token = page_token
                    db.commit()
                    return ExternalResourceModel(**resource.__dict__)
                else:
                    log.warning(f"External resource with ID {resource_id} not found.")
                    return None
            except Exception as e:
                log.error(f"Error updating last sync and page token for external resource ID {resource_id}: {e}")
                return None

    def update_resource_sync_status(self, resource_id: int, sync_enabled: bool) -> Optional[ExternalResourceModel]:
        with get_db() as db:
            try:
                resource = db.query(ExternalResource).filter_by(id=resource_id).first()
                if resource:
                    resource.sync_enabled = sync_enabled
                    db.commit()
                    return ExternalResourceModel(**resource.__dict__)
            except Exception as e:
                log.error(f"Error updating sync status for external resource ID {resource_id}: {e}")
                return None

    def update_sync_interval(self, resource_id: int, sync_interval: int) -> Optional[ExternalResourceModel]:
        with get_db() as db:
            try:
                resource = db.query(ExternalResource).filter_by(id=resource_id).first()
                if resource:
                    resource.sync_interval = sync_interval
                    db.commit()
                    return ExternalResourceModel(**resource.__dict__)
            except Exception as e:
                log.error(f"Error updating sync interval for external resource ID {resource_id}: {e}")
                return None

    def delete_resource_by_id(self, resource_id: int) -> bool:  # Renamed method
        with get_db() as db:
            try:
                resource = db.query(ExternalResource).filter_by(id=resource_id).first()
                if resource:
                    db.delete(resource)
                    db.commit()
                    log.info(f"External resource {resource_id} and all associated files deleted successfully.")
                    return True
                else:
                    log.warning(f"External resource {resource_id} not found.")
                    return False
            except Exception as e:
                log.error(f"Error deleting external resource {resource_id}: {e}")
                return False

# ================================================================
# ExternalResourcesTable Instance
# ================================================================
ExternalResources = ExternalResourcesTable() 

