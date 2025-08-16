import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Files DB Schema
####################


class File(Base):
    __tablename__ = "file"
    id = Column(String, primary_key=True)
    user_id = Column(String)
    hash = Column(Text, nullable=True)

    filename = Column(Text)
    path = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    hash: Optional[str] = None

    filename: str
    path: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: Optional[int]  # timestamp in epoch
    updated_at: Optional[int]  # timestamp in epoch
    
    @property
    def provider_info(self) -> dict:
        """Get provider information from the data field."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("provider_info", {})
        return {}
    
    @property
    def provider(self) -> Optional[str]:
        """Get the provider name."""
        return self.provider_info.get("provider")
    
    @property
    def provider_file_id(self) -> Optional[str]:
        """Get the provider's file ID."""
        return self.provider_info.get("provider_file_id")
    
    @property
    def provider_sync_enabled(self) -> bool:
        """Check if provider sync is enabled."""
        return self.provider_info.get("provider_sync_enabled", False)


####################
# Forms
####################


class FileMeta(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class FileModelResponse(BaseModel):
    id: str
    user_id: str
    hash: Optional[str] = None

    filename: str
    data: Optional[dict] = None
    meta: FileMeta

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(extra="allow")


class FileMetadataResponse(BaseModel):
    id: str
    meta: dict
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class FileForm(BaseModel):
    id: str
    hash: Optional[str] = None
    filename: str
    path: str
    data: dict = {}
    meta: dict = {}
    access_control: Optional[dict] = None
    
    # Provider tracking fields - stored within the data field
    provider: Optional[str] = None  # e.g., "google_drive", "dropbox", "onedrive"
    provider_file_id: Optional[str] = None  # Provider's unique file identifier
    provider_modified_time: Optional[str] = None  # ISO timestamp of last modification on provider
    provider_sync_enabled: Optional[bool] = False  # Whether to auto-sync this file
    provider_metadata: Optional[dict] = None  # Additional provider-specific metadata


class FilesTable:
    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        with get_db() as db:
            # Extract provider fields from form_data
            form_dict = form_data.model_dump()
            provider_fields = {
                "provider": form_dict.pop("provider", None),
                "provider_file_id": form_dict.pop("provider_file_id", None),
                "provider_modified_time": form_dict.pop("provider_modified_time", None),
                "provider_sync_enabled": form_dict.pop("provider_sync_enabled", False),
                "provider_metadata": form_dict.pop("provider_metadata", None),
            }
            
            # Add provider fields to data field if they have values
            if any(v is not None for v in provider_fields.values()):
                # Ensure data field exists
                if "data" not in form_dict:
                    form_dict["data"] = {}
                
                # Store provider fields in data
                form_dict["data"]["provider_info"] = {
                    k: v for k, v in provider_fields.items() if v is not None
                }
            
            file = FileModel(
                **{
                    **form_dict,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = File(**file.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FileModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting a new file: {e}")
                return None

    def get_file_by_id(self, id: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileModel.model_validate(file)
            except Exception:
                return None

    def get_file_provider_info(self, id: str) -> Optional[dict]:
        """Get provider information for a file."""
        file = self.get_file_by_id(id)
        if file and file.data and isinstance(file.data, dict):
            return file.data.get("provider_info", {})
        return None

    def get_file_metadata_by_id(self, id: str) -> Optional[FileMetadataResponse]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileMetadataResponse(
                    id=file.id,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
            except Exception:
                return None

    def get_files(self) -> list[FileModel]:
        with get_db() as db:
            return [FileModel.model_validate(file) for file in db.query(File).all()]

    def get_files_by_ids(self, ids: list[str]) -> list[FileModel]:
        with get_db() as db:
            return [
                FileModel.model_validate(file)
                for file in db.query(File)
                .filter(File.id.in_(ids))
                .order_by(File.updated_at.desc())
                .all()
            ]

    def get_file_metadatas_by_ids(self, ids: list[str]) -> list[FileMetadataResponse]:
        with get_db() as db:
            return [
                FileMetadataResponse(
                    id=file.id,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
                for file in db.query(File)
                .filter(File.id.in_(ids))
                .order_by(File.updated_at.desc())
                .all()
            ]

    def get_files_by_user_id(self, user_id: str) -> list[FileModel]:
        with get_db() as db:
            return [
                FileModel.model_validate(file)
                for file in db.query(File).filter_by(user_id=user_id).all()
            ]

    def get_files_by_provider(
        self, provider: str, user_id: Optional[str] = None
    ) -> list[FileModel]:
        """Get all files from a specific provider, optionally filtered by user."""
        with get_db() as db:
            query = db.query(File)
            
            # Filter by user if specified
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            # Get all files and filter by provider in Python
            # (SQLAlchemy JSON field querying can be complex across different databases)
            files = []
            for file in query.all():
                if file.data and isinstance(file.data, dict):
                    provider_info = file.data.get("provider_info", {})
                    if provider_info.get("provider") == provider:
                        files.append(FileModel.model_validate(file))
            
            return files

    def update_file_hash_by_id(self, id: str, hash: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.hash = hash
                db.commit()

                return FileModel.model_validate(file)
            except Exception:
                return None

    def update_file_data_by_id(self, id: str, data: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.data = {**(file.data if file.data else {}), **data}
                db.commit()
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file data: {e}")
                return None

    def update_file_metadata_by_id(self, id: str, meta: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.meta = {**(file.meta if file.meta else {}), **meta}
                db.commit()
                return FileModel.model_validate(file)
            except Exception:
                return None

    def update_file_provider_info_by_id(
        self, 
        id: str, 
        provider: Optional[str] = None,
        provider_file_id: Optional[str] = None,
        provider_modified_time: Optional[str] = None,
        provider_sync_enabled: Optional[bool] = None,
        provider_metadata: Optional[dict] = None
    ) -> Optional[FileModel]:
        """Update provider information for a file."""
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                if not file:
                    return None
                
                # Ensure data field exists
                if not file.data:
                    file.data = {}
                
                # Ensure provider_info exists in data
                if "provider_info" not in file.data:
                    file.data["provider_info"] = {}
                
                # Update provider fields
                updates = {
                    "provider": provider,
                    "provider_file_id": provider_file_id,
                    "provider_modified_time": provider_modified_time,
                    "provider_sync_enabled": provider_sync_enabled,
                    "provider_metadata": provider_metadata,
                }
                
                # Only update non-None values
                for key, value in updates.items():
                    if value is not None:
                        file.data["provider_info"][key] = value
                
                file.updated_at = int(time.time())
                db.commit()
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file provider info: {e}")
                return None

    def delete_file_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                db.query(File).filter_by(id=id).delete()
                db.commit()

                return True
            except Exception:
                return False

    def delete_all_files(self) -> bool:
        with get_db() as db:
            try:
                db.query(File).delete()
                db.commit()

                return True
            except Exception:
                return False


Files = FilesTable()
