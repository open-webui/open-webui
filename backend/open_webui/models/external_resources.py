"""
External Resources Model for Google Drive and other external storage integrations.

This module provides database models and CRUD operations for managing external
resource links (like Google Drive folders) that can be synced with knowledge bases.
"""

import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context

log = logging.getLogger(__name__)


####################
# ExternalResource DB Schema
####################


class ExternalResource(Base):
    """SQLAlchemy model for external resource links."""

    __tablename__ = 'external_resource'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    knowledge_id = Column(Text, ForeignKey('knowledge.id', ondelete='CASCADE'), nullable=False, index=True)

    # Resource details
    resource_type = Column(String(50), nullable=False, default='google_drive')  # google_drive, onedrive, etc.
    resource_link = Column(Text, nullable=False)
    resource_name = Column(Text, nullable=True)

    # Sync configuration
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=60)  # Default: sync every hour

    # Sync state
    page_token = Column(Text, nullable=True)  # For incremental sync
    last_synced_at = Column(BigInteger, nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # success, failed, in_progress
    last_sync_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


####################
# Pydantic Models
####################


class ExternalResourceModel(BaseModel):
    """Pydantic model for external resource validation and serialization."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    knowledge_id: str

    resource_type: str = 'google_drive'
    resource_link: str
    resource_name: Optional[str] = None

    sync_enabled: bool = True
    sync_interval_minutes: int = 60

    page_token: Optional[str] = None
    last_synced_at: Optional[int] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None

    created_at: int
    updated_at: int


class ExternalResourceCreateForm(BaseModel):
    """Form for creating a new external resource."""

    knowledge_id: str
    resource_type: str = Field(default='google_drive', pattern='^(google_drive|onedrive|dropbox)$')
    resource_link: str
    resource_name: Optional[str] = None
    sync_enabled: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)  # 5 min to 24 hours


class ExternalResourceUpdateForm(BaseModel):
    """Form for updating an external resource."""

    resource_name: Optional[str] = None
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(default=None, ge=5, le=1440)


class ExternalResourceResponse(ExternalResourceModel):
    """Response model for external resource API endpoints."""

    pass


####################
# Table Operations
####################


class ExternalResourcesTable:
    """CRUD operations for external resources."""

    def insert_new_resource(
        self,
        user_id: str,
        form_data: ExternalResourceCreateForm,
        db: Optional[Session] = None,
    ) -> Optional[ExternalResourceModel]:
        """Create a new external resource."""
        with get_db_context(db) as db:
            now = int(time.time())
            resource = ExternalResource(
                id=str(uuid.uuid4()),
                user_id=user_id,
                knowledge_id=form_data.knowledge_id,
                resource_type=form_data.resource_type,
                resource_link=form_data.resource_link,
                resource_name=form_data.resource_name,
                sync_enabled=form_data.sync_enabled,
                sync_interval_minutes=form_data.sync_interval_minutes,
                created_at=now,
                updated_at=now,
            )

            try:
                db.add(resource)
                db.commit()
                db.refresh(resource)
                return ExternalResourceModel.model_validate(resource)
            except Exception as e:
                log.error(f'Failed to create external resource: {e}')
                db.rollback()
                return None

    def get_resource_by_id(
        self,
        resource_id: str,
        db: Optional[Session] = None,
    ) -> Optional[ExternalResourceModel]:
        """Get an external resource by its ID."""
        with get_db_context(db) as db:
            resource = db.query(ExternalResource).filter_by(id=resource_id).first()
            return ExternalResourceModel.model_validate(resource) if resource else None

    def get_resources_by_knowledge_id(
        self,
        knowledge_id: str,
        db: Optional[Session] = None,
    ) -> list[ExternalResourceModel]:
        """Get all external resources for a knowledge base."""
        with get_db_context(db) as db:
            resources = (
                db.query(ExternalResource)
                .filter_by(knowledge_id=knowledge_id)
                .order_by(ExternalResource.created_at.desc())
                .all()
            )
            return [ExternalResourceModel.model_validate(r) for r in resources]

    def get_resources_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> list[ExternalResourceModel]:
        """Get all external resources created by a user."""
        with get_db_context(db) as db:
            resources = (
                db.query(ExternalResource)
                .filter_by(user_id=user_id)
                .order_by(ExternalResource.created_at.desc())
                .all()
            )
            return [ExternalResourceModel.model_validate(r) for r in resources]

    def get_resources_pending_sync(
        self,
        db: Optional[Session] = None,
    ) -> list[ExternalResourceModel]:
        """Get all resources that need to be synced."""
        with get_db_context(db) as db:
            now = int(time.time())
            resources = (
                db.query(ExternalResource)
                .filter(
                    ExternalResource.sync_enabled == True,  # noqa: E712
                    (
                        (ExternalResource.last_synced_at == None)  # noqa: E711
                        | (ExternalResource.last_synced_at + ExternalResource.sync_interval_minutes * 60 < now)
                    ),
                )
                .all()
            )
            return [ExternalResourceModel.model_validate(r) for r in resources]

    def update_resource(
        self,
        resource_id: str,
        form_data: ExternalResourceUpdateForm,
        db: Optional[Session] = None,
    ) -> Optional[ExternalResourceModel]:
        """Update an external resource."""
        with get_db_context(db) as db:
            update_data = {k: v for k, v in form_data.model_dump().items() if v is not None}
            update_data['updated_at'] = int(time.time())

            try:
                db.query(ExternalResource).filter_by(id=resource_id).update(update_data)
                db.commit()
                return self.get_resource_by_id(resource_id, db=db)
            except Exception as e:
                log.error(f'Failed to update external resource {resource_id}: {e}')
                db.rollback()
                return None

    def update_sync_status(
        self,
        resource_id: str,
        status: str,
        error: Optional[str] = None,
        page_token: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Update the sync status of a resource."""
        with get_db_context(db) as db:
            now = int(time.time())
            update_data = {
                'last_sync_status': status,
                'last_sync_error': error,
                'updated_at': now,
            }

            if status == 'success':
                update_data['last_synced_at'] = now
                update_data['last_sync_error'] = None

            if page_token is not None:
                update_data['page_token'] = page_token

            try:
                db.query(ExternalResource).filter_by(id=resource_id).update(update_data)
                db.commit()
                return True
            except Exception as e:
                log.error(f'Failed to update sync status for {resource_id}: {e}')
                db.rollback()
                return False

    def delete_resource_by_id(
        self,
        resource_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete an external resource."""
        with get_db_context(db) as db:
            try:
                db.query(ExternalResource).filter_by(id=resource_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.error(f'Failed to delete external resource {resource_id}: {e}')
                db.rollback()
                return False

    def delete_resources_by_knowledge_id(
        self,
        knowledge_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete all external resources for a knowledge base."""
        with get_db_context(db) as db:
            try:
                db.query(ExternalResource).filter_by(knowledge_id=knowledge_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.error(f'Failed to delete resources for knowledge {knowledge_id}: {e}')
                db.rollback()
                return False


# Global instance
ExternalResources = ExternalResourcesTable()
