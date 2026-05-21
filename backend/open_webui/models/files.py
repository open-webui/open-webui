"""File upload models, forms, and database operations."""

from __future__ import annotations

import logging
import time
# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.utils.misc import sanitize_metadata
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import JSON, BigInteger, Column, String, Text, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class File(Base):  # uploaded file record
    __tablename__ = 'file'
    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)  # owner user id
    hash = Column(Text, nullable=True)

    filename = Column(Text)  # original upload filename
    path = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger, index=True)  # upload timestamp
    updated_at = Column(BigInteger)


class FileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    hash: str | None = None

    filename: str
    path: str | None = None

    data: dict | None = None
    meta: dict | None = None

    created_at: int | None  # timestamp in epoch
    updated_at: int | None  # timestamp in epoch

# --- metadata structures ---
class FileMeta(BaseModel):
    name: str | None = None
    content_type: str | None = None
    size: int | None = None

    model_config = ConfigDict(extra='allow')

    @model_validator(mode='before')
    @classmethod
    def sanitize_meta(cls, data):
        """Sanitize metadata fields to handle malformed legacy data."""
        if not isinstance(data, dict):
            return data

        # Handle content_type that may be a list like ['application/pdf', None]
        content_type = data.get('content_type')
        if isinstance(content_type, list):
            # Extract first non-None string value
            data['content_type'] = next((item for item in content_type if isinstance(item, str)), None)
        elif content_type is not None and not isinstance(content_type, str):
            data['content_type'] = None

        return data


class FileModelResponse(BaseModel):
    id: str
    user_id: str
    hash: str | None = None

    filename: str
    data: dict | None = None
    meta: FileMeta | None = None

    created_at: int  # timestamp in epoch
    updated_at: int | None = None  # timestamp in epoch, optional for legacy files

    model_config = ConfigDict(extra='allow')


class FileMetadataResponse(BaseModel):
    id: str
    hash: str | None = None
    meta: dict | None = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class FileListResponse(BaseModel):
    items: list[FileModelResponse]
    total: int


class FileForm(BaseModel):
    id: str
    hash: str | None = None
    filename: str
    path: str
    data: dict = {}
    meta: dict = {}


class FileUpdateForm(BaseModel):
    hash: str | None = None
    data: dict | None = None
    meta: dict | None = None


class FilesTable:
    async def insert_new_file(
        self, user_id: str, form_data: FileForm, db: AsyncSession | None = None
    ) -> FileModel | None:
        async with get_async_db_context(db) as db:
            file_data = form_data.model_dump()

            # Sanitize meta to remove non-JSON-serializable objects
            # (e.g. callable tool functions, MCP client instances from middleware)
            if file_data.get('meta'):
                file_data['meta'] = sanitize_metadata(file_data['meta'])

            file = FileModel(
                **{
                    **file_data,
                    'user_id': user_id,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )

            try:
                result = File(**file.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FileModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f'Error inserting a new file: {e}')
                return None  # insertion failed

    async def get_file_by_id(
        self, id: str, db: AsyncSession | None = None,
    ) -> FileModel | None:
        """Look up a file by its primary key."""
        try:
            async with get_async_db_context(db) as db:
                file = await db.get(File, id)
                if not file:
                    return None
                return FileModel.model_validate(file)
        except Exception:
            return None

    async def get_file_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id, user_id=user_id))
                file = result.scalars().first()
                if file:
                    return FileModel.model_validate(file)
                else:
                    return None
            except Exception:
                return None

    async def get_file_metadata_by_id(self, id: str, db: AsyncSession | None = None) -> FileMetadataResponse | None:
        async with get_async_db_context(db) as db:
            try:
                file = await db.get(File, id)
                if not file:
                    return None
                return FileMetadataResponse(
                    id=file.id,
                    hash=file.hash,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
            except Exception:
                return None

    async def get_files(self, db: AsyncSession | None = None) -> list[FileModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(File))
            return [FileModel.model_validate(file) for file in result.scalars().all()]

    async def check_access_by_user_id(self, id, user_id, permission='write', db: AsyncSession | None = None) -> bool:
        file = await self.get_file_by_id(id, db=db)
        if not file:
            return False
        if file.user_id == user_id:
            return True
        # Implement additional access control logic here as needed
        return False

    async def get_files_by_ids(self, ids: list[str], db: AsyncSession | None = None) -> list[FileModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(File).filter(File.id.in_(ids)).order_by(File.updated_at.desc()))
            return [FileModel.model_validate(file) for file in result.scalars().all()]

    async def get_file_metadatas_by_ids(
        self, ids: list[str], db: AsyncSession | None = None
    ) -> list[FileMetadataResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(File.id, File.hash, File.meta, File.created_at, File.updated_at)
                .filter(File.id.in_(ids))
                .order_by(File.updated_at.desc())
            )
            return [
                FileMetadataResponse(
                    id=row.id,
                    hash=row.hash,
                    meta=row.meta,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in result.all()
            ]

    async def get_files_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[FileModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(File).filter_by(user_id=user_id))
            return [FileModel.model_validate(file) for file in result.scalars().all()]

    async def get_file_list(
        self,
        user_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> 'FileListResponse':
        async with get_async_db_context(db) as db:
            stmt = select(File)
            if user_id:
                stmt = stmt.filter_by(user_id=user_id)

            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            result = await db.execute(stmt.order_by(File.updated_at.desc(), File.id.desc()).offset(skip).limit(limit))
            items = [FileModelResponse.model_validate(file, from_attributes=True) for file in result.scalars().all()]

            return FileListResponse(items=items, total=total)

    @staticmethod
    def _glob_to_like_pattern(glob: str) -> str:
        """
        Convert a glob/fnmatch pattern to a SQL LIKE pattern.

        Escapes SQL special characters and converts glob wildcards:
        - `*` becomes `%` (match any sequence of characters)
        - `?` becomes `_` (match exactly one character)

        Args:
            glob: A glob pattern (e.g., "*.txt", "file?.doc")

        Returns:
            A SQL LIKE compatible pattern with proper escaping.
        """
        # Escape SQL special characters first, then convert glob wildcards
        pattern = glob.replace('\\', '\\\\')
        pattern = pattern.replace('%', '\\%')
        pattern = pattern.replace('_', '\\_')
        pattern = pattern.replace('*', '%')
        pattern = pattern.replace('?', '_')
        return pattern

    async def search_files(
        self,
        user_id: str | None = None,
        filename: str = '*',
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession | None = None,
    ) -> list[FileModel]:
        """
        Search files with glob pattern matching, optional user filter, and pagination.

        Args:
            user_id: Filter by user ID. If None, returns files for all users.
            filename: Glob pattern to match filenames (e.g., "*.txt"). Default "*" matches all.
            skip: Number of results to skip for pagination.
            limit: Maximum number of results to return.
            db: Optional database session.

        Returns:
            List of matching FileModel objects, ordered by created_at descending.
        """
        async with get_async_db_context(db) as db:
            stmt = select(File)

            if user_id:
                stmt = stmt.filter_by(user_id=user_id)

            pattern = self._glob_to_like_pattern(filename)
            if pattern != '%':
                stmt = stmt.filter(File.filename.ilike(pattern, escape='\\'))

            result = await db.execute(stmt.order_by(File.created_at.desc(), File.id.desc()).offset(skip).limit(limit))
            return [FileModel.model_validate(file) for file in result.scalars().all()]

    async def update_file_by_id(
        self, id: str, form_data: FileUpdateForm, db: AsyncSession | None = None
    ) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id))
                file = result.scalars().first()

                if form_data.hash is not None:
                    file.hash = form_data.hash

                if form_data.data is not None:
                    file.data = {**(file.data if file.data else {}), **form_data.data}

                if form_data.meta is not None:
                    file.meta = {**(file.meta if file.meta else {}), **form_data.meta}

                file.updated_at = int(time.time())
                await db.commit()
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f'Error updating file completely by id: {e}')
                return None

    async def update_file_hash_by_id(
        self, id: str, hash: str | None, db: AsyncSession | None = None
    ) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id))
                file = result.scalars().first()
                file.hash = hash
                file.updated_at = int(time.time())
                await db.commit()

                return FileModel.model_validate(file)
            except Exception:
                return None

    async def update_file_data_by_id(self, id: str, data: dict, db: AsyncSession | None = None) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id))
                file = result.scalars().first()
                file.data = {**(file.data if file.data else {}), **data}
                file.updated_at = int(time.time())
                await db.commit()
                return FileModel.model_validate(file)
            except Exception as e:
                return None

    async def update_file_metadata_by_id(self, id: str, meta: dict, db: AsyncSession | None = None) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id))
                file = result.scalars().first()
                file.meta = {**(file.meta if file.meta else {}), **meta}
                file.updated_at = int(time.time())
                await db.commit()
                return FileModel.model_validate(file)
            except Exception:
                return None

    async def update_file_name_by_id(self, id: str, name: str, db: AsyncSession | None = None) -> FileModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(File).filter_by(id=id))
                file = result.scalars().first()
                file.filename = name
                file.meta = {**(file.meta if file.meta else {}), 'name': name}
                file.updated_at = int(time.time())
                await db.commit()
                return FileModel.model_validate(file)
            except Exception:
                return None

    async def delete_file_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(File).filter_by(id=id))
                await db.commit()

                return True
            except Exception:
                return False

    async def delete_all_files(self, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(File))
                await db.commit()

                return True
            except Exception:
                return False


Files = FilesTable()  # singleton files repository
