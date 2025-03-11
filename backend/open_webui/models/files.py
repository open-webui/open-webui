import logging
import time
from typing import Optional
import uuid
from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from open_webui.models.externalResources import ExternalResources
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])
####################
# Files DB Schema
####################
class File(Base):
    __tablename__ = "file"
    id = Column(String, primary_key=True)
    file_id = Column(String, nullable=True)  # Google Drive file ID for external files
    user_id = Column(String)
    hash = Column(Text, nullable=True)
    md5_hash = Column(Text, nullable=True)  # New column for storing MD5 hash
    modified_time = Column(String, nullable=True)  # Google Drive's `modifiedTime` for detecting changes in Google-native files
    filename = Column(Text)
    path = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    # New additions
    external_source_id = Column(Integer, ForeignKey("external_resources.id"), nullable=True)  # Snake case
    external_resource = relationship("ExternalResource", back_populates="files")

class FileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file_id: Optional[str] = None
    user_id: str
    hash: Optional[str] = None
    md5_hash: Optional[str] = None  # Added new MD5 hash field
    modified_time: Optional[str] = None
    filename: str
    path: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    external_source_id: Optional[int] = None
    access_control: Optional[dict] = None
    created_at: Optional[int]  # timestamp in epoch
    updated_at: Optional[int]  # timestamp in epoch

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
    file_id: Optional[str] = None
    user_id: str
    hash: Optional[str] = None
    md5_hash: Optional[str] = None  # Added new MD5 hash field
    modified_time: Optional[str] = None
    filename: str
    data: Optional[dict] = None
    meta: FileMeta
    external_resource_id: Optional[int] = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    model_config = ConfigDict(extra="allow")

class FileMetadataResponse(BaseModel):
    id: str
    file_id: Optional[str] = None
    meta: dict
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    modified_time: Optional[str] = None
    external_resource_id: Optional[int] = None

class FileForm(BaseModel):
    id: str
    file_id: Optional[str] = None
    hash: Optional[str] = None
    md5_hash: Optional[str] = None  # Added field to accept MD5 hash
    filename: str
    path: str
    data: dict = {}
    meta: dict = {}
    modified_time: Optional[str] = None
    access_control: Optional[dict] = None
    external_resource_id: Optional[int] = None

class FilesTable:
    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        with get_db() as db:
            file = FileModel(
                **{
                    **form_data.model_dump(),
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
                print(f"Error creating file: {e}")
                return None
    def insert_new_external_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        """
        Insert a new file from an external source (e.g., Google Drive).
        """
        with get_db() as db:
            try:
                # Retain metadata from Google Drive in `form_data.meta`
                unique_id = str(uuid.uuid4())  # Generate a unique ID for the database
                print(unique_id)
                file_data = {
                    "id": unique_id,  # Assign generated unique ID for internal use
                    "file_id": form_data.id,  # External Google Drive file ID
                    "user_id": user_id,
                    "filename": form_data.filename,
                    "path": form_data.path,  # Path to the uploaded file
                    "hash": None,  # Keep general hash as None
                    "md5_hash": form_data.meta.get("md5"),  # Use MD5 checksum from meta
                    "modified_time": form_data.meta.get("modified_time"),  # Google's `modifiedTime`
                    "meta": form_data.meta,  # Retain metadata (including name, content_type, size)
                    "data": form_data.data,  # Additional data is stored here
                    "access_control": form_data.access_control,
                    "external_source_id": form_data.external_resource_id,  # External resource linkage
                    "created_at": int(time.time()),  # Unix epoch time
                    "updated_at": int(time.time()),  # Unix epoch time
                }
                # Create and validate Pydantic `FileModel`
                file_model = FileModel(**file_data)
                # Insert record into database using SQLAlchemy ORM
                orm_file = File(**file_data)
                db.add(orm_file)
                db.commit()
                db.refresh(orm_file)
                print("Drive file uploaded successfully.")
                return FileModel.model_validate(orm_file)
            except Exception as e:
                log.error(f"Error inserting external file: {str(e)}")
                return None
    def get_file_by_id(self, id: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileModel.model_validate(file)
            except Exception:
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
    def get_files_by_external_resource_id(self, external_resource_id: int) -> list[FileModel]:
        with get_db() as db:
            try:
                files = (
                    db.query(File)
                    .filter(File.external_source_id == external_resource_id)
                    .order_by(File.updated_at.desc())
                    .all()
                )
                return [FileModel.model_validate(file) for file in files]
            except Exception as e:
                log.error(f"Error fetching files by external_resource_id {external_resource_id}: {e}")
                return []

Files = FilesTable()
