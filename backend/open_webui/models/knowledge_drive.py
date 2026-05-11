"""
Knowledge Drive Source Database Model

Tracks Google Drive folder connections to Knowledge bases for automatic syncing.
Follows the same patterns as Gmail sync for consistency.
"""

import time
import logging
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Boolean, Index

from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Knowledge Drive Source DB Schema
####################


class KnowledgeDriveSource(Base):
    """
    Database model for tracking Google Drive folder connections to Knowledge bases.

    Each Knowledge base can have multiple Drive folders connected.
    Each folder is synced independently with its own change tracking.
    """

    __tablename__ = "knowledge_drive_source"

    id = Column(Text, primary_key=True)
    knowledge_id = Column(Text, nullable=False, index=True)  # FK to knowledge.id
    user_id = Column(Text, nullable=False, index=True)  # Owner who connected the drive

    # Google Drive folder info
    drive_folder_id = Column(Text, nullable=False)  # Google Drive folder ID
    drive_folder_name = Column(Text, nullable=True)  # Display name for UI
    drive_folder_path = Column(Text, nullable=True)  # Full path for display
    shared_drive_id = Column(Text, nullable=True)  # Shared Drive ID (if folder is in a Shared Drive)
    recursive = Column(Boolean, default=False)  # Whether to sync subfolders recursively

    # Sync tracking
    last_sync_timestamp = Column(BigInteger, nullable=True)  # Unix timestamp of last sync
    last_sync_change_token = Column(Text, nullable=True)  # Drive API start page token for changes
    last_sync_file_count = Column(Integer, default=0)  # Files synced in last run

    # Sync status: "never", "active", "completed", "paused", "error"
    sync_status = Column(String, default="never")
    sync_enabled = Column(Boolean, default=True)  # Whether auto-sync is enabled
    auto_sync_interval_hours = Column(Integer, default=1)  # How often to sync

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_knowledge_drive_source_knowledge_id", "knowledge_id"),
        Index("idx_knowledge_drive_source_user_id", "user_id"),
        Index("idx_knowledge_drive_source_sync_status", "sync_status"),
    )


class KnowledgeDriveSourceModel(BaseModel):
    """Pydantic model for Knowledge Drive Source"""

    id: str
    knowledge_id: str
    user_id: str

    drive_folder_id: str
    drive_folder_name: Optional[str] = None
    drive_folder_path: Optional[str] = None
    shared_drive_id: Optional[str] = None  # Shared Drive ID if folder is in a Shared Drive
    recursive: bool = False

    last_sync_timestamp: Optional[int] = None
    last_sync_change_token: Optional[str] = None
    last_sync_file_count: int = 0

    sync_status: str = "never"
    sync_enabled: bool = True
    auto_sync_interval_hours: int = 1

    last_error: Optional[str] = None
    error_count: int = 0

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Knowledge Drive File DB Schema
####################


class KnowledgeDriveFile(Base):
    """
    Database model for tracking individual files synced from Google Drive.

    Used to detect changes (modified, deleted, new files) during sync.
    """

    __tablename__ = "knowledge_drive_file"

    id = Column(Text, primary_key=True)
    drive_source_id = Column(Text, nullable=False, index=True)  # FK to knowledge_drive_source.id
    knowledge_id = Column(Text, nullable=False, index=True)  # FK to knowledge.id
    file_id = Column(Text, nullable=True, index=True)  # FK to file.id (Open WebUI file)

    # Google Drive file info
    drive_file_id = Column(Text, nullable=False)  # Google Drive file ID
    drive_file_name = Column(Text, nullable=False)  # Filename in Drive
    drive_file_mime_type = Column(Text, nullable=True)  # MIME type
    drive_file_size = Column(BigInteger, nullable=True)  # File size in bytes
    drive_file_md5 = Column(Text, nullable=True)  # MD5 checksum for change detection
    drive_file_modified_time = Column(Text, nullable=True)  # ISO timestamp from Drive

    # Sync tracking
    last_sync_timestamp = Column(BigInteger, nullable=True)
    sync_status = Column(String, default="pending")  # "pending", "synced", "error", "deleted"

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_knowledge_drive_file_source_id", "drive_source_id"),
        Index("idx_knowledge_drive_file_knowledge_id", "knowledge_id"),
        Index("idx_knowledge_drive_file_drive_id", "drive_file_id"),
    )


class KnowledgeDriveFileModel(BaseModel):
    """Pydantic model for Knowledge Drive File"""

    id: str
    drive_source_id: str
    knowledge_id: str
    file_id: Optional[str] = None

    drive_file_id: str
    drive_file_name: str
    drive_file_mime_type: Optional[str] = None
    drive_file_size: Optional[int] = None
    drive_file_md5: Optional[str] = None
    drive_file_modified_time: Optional[str] = None

    last_sync_timestamp: Optional[int] = None
    sync_status: str = "pending"

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class KnowledgeDriveSourceForm(BaseModel):
    """Form for connecting a Drive folder to a Knowledge base"""

    drive_folder_id: str
    drive_folder_name: Optional[str] = None
    drive_folder_path: Optional[str] = None
    shared_drive_id: Optional[str] = None  # Shared Drive ID if folder is in a Shared Drive
    recursive: bool = False  # Whether to sync subfolders recursively
    auto_sync_interval_hours: int = 1


class KnowledgeDriveSourceResponse(BaseModel):
    """Response model for Drive source (includes file count)"""

    id: str
    knowledge_id: str
    drive_folder_id: str
    drive_folder_name: Optional[str] = None
    drive_folder_path: Optional[str] = None
    shared_drive_id: Optional[str] = None
    recursive: bool = False
    sync_status: str
    sync_enabled: bool
    last_sync_timestamp: Optional[int] = None
    last_sync_file_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    created_at: int


####################
# Database Operations
####################


class KnowledgeDriveSourceTable:
    """Database operations for Knowledge Drive Sources"""

    def create_drive_source(
        self,
        knowledge_id: str,
        user_id: str,
        form_data: KnowledgeDriveSourceForm,
    ) -> Optional[KnowledgeDriveSourceModel]:
        """Create a new Drive source connection for a Knowledge base"""
        try:
            with get_db() as db:
                now = int(time.time())
                source = KnowledgeDriveSource(
                    id=str(uuid.uuid4()),
                    knowledge_id=knowledge_id,
                    user_id=user_id,
                    drive_folder_id=form_data.drive_folder_id,
                    drive_folder_name=form_data.drive_folder_name,
                    drive_folder_path=form_data.drive_folder_path,
                    shared_drive_id=form_data.shared_drive_id,
                    recursive=form_data.recursive,
                    auto_sync_interval_hours=form_data.auto_sync_interval_hours,
                    created_at=now,
                    updated_at=now,
                )
                db.add(source)
                db.commit()
                db.refresh(source)
                log.info(
                    f"Created Drive source {source.id} for knowledge {knowledge_id} "
                    f"(recursive={form_data.recursive})"
                )
                return KnowledgeDriveSourceModel.model_validate(source)
        except Exception as e:
            log.error(f"Error creating Drive source: {e}")
            return None

    def get_drive_source_by_id(self, source_id: str) -> Optional[KnowledgeDriveSourceModel]:
        """Get a Drive source by ID"""
        try:
            with get_db() as db:
                source = db.query(KnowledgeDriveSource).filter_by(id=source_id).first()
                if source:
                    return KnowledgeDriveSourceModel.model_validate(source)
                return None
        except Exception as e:
            log.error(f"Error getting Drive source {source_id}: {e}")
            return None

    def get_drive_sources_by_knowledge_id(self, knowledge_id: str) -> List[KnowledgeDriveSourceModel]:
        """Get all Drive sources for a Knowledge base"""
        try:
            with get_db() as db:
                sources = (
                    db.query(KnowledgeDriveSource)
                    .filter_by(knowledge_id=knowledge_id)
                    .order_by(KnowledgeDriveSource.created_at.desc())
                    .all()
                )
                return [KnowledgeDriveSourceModel.model_validate(s) for s in sources]
        except Exception as e:
            log.error(f"Error getting Drive sources for knowledge {knowledge_id}: {e}")
            return []

    def get_drive_sources_by_user_id(self, user_id: str) -> List[KnowledgeDriveSourceModel]:
        """Get all Drive sources for a user"""
        try:
            with get_db() as db:
                sources = (
                    db.query(KnowledgeDriveSource)
                    .filter_by(user_id=user_id)
                    .order_by(KnowledgeDriveSource.updated_at.desc())
                    .all()
                )
                return [KnowledgeDriveSourceModel.model_validate(s) for s in sources]
        except Exception as e:
            log.error(f"Error getting Drive sources for user {user_id}: {e}")
            return []

    def get_sources_needing_sync(self, max_hours_since_sync: float = 1) -> List[KnowledgeDriveSourceModel]:
        """
        Get Drive sources that need syncing based on their interval.

        Used by the periodic sync scheduler.
        """
        try:
            with get_db() as db:
                cutoff_time = int(time.time() - (max_hours_since_sync * 3600))

                sources = (
                    db.query(KnowledgeDriveSource)
                    .filter(
                        KnowledgeDriveSource.sync_enabled == True,
                        KnowledgeDriveSource.sync_status != "active",
                        (
                            (KnowledgeDriveSource.last_sync_timestamp == None)
                            | (KnowledgeDriveSource.last_sync_timestamp < cutoff_time)
                        ),
                    )
                    .all()
                )
                return [KnowledgeDriveSourceModel.model_validate(s) for s in sources]
        except Exception as e:
            log.error(f"Error getting sources needing sync: {e}")
            return []

    def update_drive_source(self, source_id: str, **updates) -> Optional[KnowledgeDriveSourceModel]:
        """Update a Drive source with given fields"""
        try:
            with get_db() as db:
                source = db.query(KnowledgeDriveSource).filter_by(id=source_id).first()
                if not source:
                    return None

                valid_fields = {
                    "drive_folder_name",
                    "drive_folder_path",
                    "shared_drive_id",
                    "recursive",
                    "last_sync_timestamp",
                    "last_sync_change_token",
                    "last_sync_file_count",
                    "sync_status",
                    "sync_enabled",
                    "auto_sync_interval_hours",
                    "last_error",
                    "error_count",
                }

                for key, value in updates.items():
                    if key in valid_fields and hasattr(source, key):
                        setattr(source, key, value)

                source.updated_at = int(time.time())
                db.commit()
                db.refresh(source)
                return KnowledgeDriveSourceModel.model_validate(source)
        except Exception as e:
            log.error(f"Error updating Drive source {source_id}: {e}")
            return None

    def mark_sync_start(self, source_id: str) -> Optional[KnowledgeDriveSourceModel]:
        """Mark a Drive source sync as starting"""
        return self.update_drive_source(
            source_id,
            sync_status="active",
            error_count=0,
            last_error=None,
        )

    def mark_sync_complete(
        self,
        source_id: str,
        files_synced: int,
        change_token: Optional[str] = None,
    ) -> Optional[KnowledgeDriveSourceModel]:
        """Mark a Drive source sync as completed"""
        return self.update_drive_source(
            source_id,
            sync_status="completed",
            last_sync_timestamp=int(time.time()),
            last_sync_file_count=files_synced,
            last_sync_change_token=change_token,
        )

    def mark_sync_error(self, source_id: str, error_message: str) -> Optional[KnowledgeDriveSourceModel]:
        """Mark a Drive source sync as failed"""
        try:
            with get_db() as db:
                source = db.query(KnowledgeDriveSource).filter_by(id=source_id).first()
                if not source:
                    return None

                source.sync_status = "error"
                source.last_error = error_message[:500]  # Truncate long errors
                source.error_count = source.error_count + 1
                source.updated_at = int(time.time())
                db.commit()
                db.refresh(source)
                return KnowledgeDriveSourceModel.model_validate(source)
        except Exception as e:
            log.error(f"Error marking sync error for {source_id}: {e}")
            return None

    def delete_drive_source(self, source_id: str) -> bool:
        """Delete a Drive source and its tracked files"""
        try:
            with get_db() as db:
                # Delete tracked files first
                db.query(KnowledgeDriveFile).filter_by(drive_source_id=source_id).delete()

                # Delete the source
                result = db.query(KnowledgeDriveSource).filter_by(id=source_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            log.error(f"Error deleting Drive source {source_id}: {e}")
            return False

    def delete_drive_sources_by_knowledge_id(self, knowledge_id: str) -> bool:
        """Delete all Drive sources for a Knowledge base"""
        try:
            with get_db() as db:
                # Get source IDs first
                sources = db.query(KnowledgeDriveSource.id).filter_by(knowledge_id=knowledge_id).all()
                source_ids = [s.id for s in sources]

                # Delete tracked files
                if source_ids:
                    db.query(KnowledgeDriveFile).filter(KnowledgeDriveFile.drive_source_id.in_(source_ids)).delete(
                        synchronize_session=False
                    )

                # Delete sources
                db.query(KnowledgeDriveSource).filter_by(knowledge_id=knowledge_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting Drive sources for knowledge {knowledge_id}: {e}")
            return False


class KnowledgeDriveFileTable:
    """Database operations for Knowledge Drive Files"""

    def create_or_update_drive_file(
        self,
        drive_source_id: str,
        knowledge_id: str,
        drive_file_id: str,
        drive_file_name: str,
        drive_file_mime_type: Optional[str] = None,
        drive_file_size: Optional[int] = None,
        drive_file_md5: Optional[str] = None,
        drive_file_modified_time: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> Optional[KnowledgeDriveFileModel]:
        """Create or update a tracked Drive file"""
        try:
            with get_db() as db:
                now = int(time.time())

                # Check if file already exists
                existing = (
                    db.query(KnowledgeDriveFile)
                    .filter_by(
                        drive_source_id=drive_source_id,
                        drive_file_id=drive_file_id,
                    )
                    .first()
                )

                if existing:
                    # Update existing
                    existing.drive_file_name = drive_file_name
                    existing.drive_file_mime_type = drive_file_mime_type
                    existing.drive_file_size = drive_file_size
                    existing.drive_file_md5 = drive_file_md5
                    existing.drive_file_modified_time = drive_file_modified_time
                    if file_id:
                        existing.file_id = file_id
                    existing.updated_at = now
                    db.commit()
                    db.refresh(existing)
                    return KnowledgeDriveFileModel.model_validate(existing)
                else:
                    # Create new
                    drive_file = KnowledgeDriveFile(
                        id=str(uuid.uuid4()),
                        drive_source_id=drive_source_id,
                        knowledge_id=knowledge_id,
                        file_id=file_id,
                        drive_file_id=drive_file_id,
                        drive_file_name=drive_file_name,
                        drive_file_mime_type=drive_file_mime_type,
                        drive_file_size=drive_file_size,
                        drive_file_md5=drive_file_md5,
                        drive_file_modified_time=drive_file_modified_time,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(drive_file)
                    db.commit()
                    db.refresh(drive_file)
                    return KnowledgeDriveFileModel.model_validate(drive_file)
        except Exception as e:
            log.error(f"Error creating/updating Drive file: {e}")
            return None

    def get_drive_files_by_source_id(self, drive_source_id: str) -> List[KnowledgeDriveFileModel]:
        """Get all tracked files for a Drive source"""
        try:
            with get_db() as db:
                files = db.query(KnowledgeDriveFile).filter_by(drive_source_id=drive_source_id).all()
                return [KnowledgeDriveFileModel.model_validate(f) for f in files]
        except Exception as e:
            log.error(f"Error getting Drive files for source {drive_source_id}: {e}")
            return []

    def get_drive_file_by_drive_id(self, drive_source_id: str, drive_file_id: str) -> Optional[KnowledgeDriveFileModel]:
        """Get a tracked file by its Drive file ID"""
        try:
            with get_db() as db:
                file = (
                    db.query(KnowledgeDriveFile)
                    .filter_by(
                        drive_source_id=drive_source_id,
                        drive_file_id=drive_file_id,
                    )
                    .first()
                )
                if file:
                    return KnowledgeDriveFileModel.model_validate(file)
                return None
        except Exception as e:
            log.error(f"Error getting Drive file {drive_file_id}: {e}")
            return None

    def update_drive_file(self, record_id: str, **updates) -> Optional[KnowledgeDriveFileModel]:
        """
        Update a tracked Drive file.

        Args:
            record_id: The KnowledgeDriveFile record ID (our tracking table ID)
            **updates: Fields to update (file_id, sync_status, etc.)
        """
        try:
            with get_db() as db:
                file = db.query(KnowledgeDriveFile).filter_by(id=record_id).first()
                if not file:
                    return None

                valid_fields = {
                    "file_id",
                    "drive_file_name",
                    "drive_file_mime_type",
                    "drive_file_size",
                    "drive_file_md5",
                    "drive_file_modified_time",
                    "last_sync_timestamp",
                    "sync_status",
                }

                for key, value in updates.items():
                    if key in valid_fields and hasattr(file, key):
                        setattr(file, key, value)

                file.updated_at = int(time.time())
                db.commit()
                db.refresh(file)
                return KnowledgeDriveFileModel.model_validate(file)
        except Exception as e:
            log.error(f"Error updating Drive file {record_id}: {e}")
            return None

    def mark_file_synced(self, drive_file_record_id: str, open_webui_file_id: str) -> Optional[KnowledgeDriveFileModel]:
        """
        Mark a Drive file as synced with its Open WebUI file ID.

        Args:
            drive_file_record_id: The KnowledgeDriveFile record ID (our tracking record)
            open_webui_file_id: The Open WebUI file ID from the Files table
        """
        return self.update_drive_file(
            drive_file_record_id,
            file_id=open_webui_file_id,
            sync_status="synced",
            last_sync_timestamp=int(time.time()),
        )

    def mark_file_deleted(self, drive_file_record_id: str) -> Optional[KnowledgeDriveFileModel]:
        """
        Mark a Drive file as deleted (no longer in Drive).

        Args:
            drive_file_record_id: The KnowledgeDriveFile record ID (our tracking record)
        """
        return self.update_drive_file(drive_file_record_id, sync_status="deleted")

    def delete_drive_file(self, file_id: str) -> bool:
        """Delete a tracked Drive file"""
        try:
            with get_db() as db:
                result = db.query(KnowledgeDriveFile).filter_by(id=file_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            log.error(f"Error deleting Drive file {file_id}: {e}")
            return False

    def delete_drive_files_by_source_id(self, drive_source_id: str) -> bool:
        """Delete all tracked files for a Drive source"""
        try:
            with get_db() as db:
                db.query(KnowledgeDriveFile).filter_by(drive_source_id=drive_source_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting Drive files for source {drive_source_id}: {e}")
            return False


# Global instances
KnowledgeDriveSources = KnowledgeDriveSourceTable()
KnowledgeDriveFiles = KnowledgeDriveFileTable()
