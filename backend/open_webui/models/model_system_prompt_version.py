"""Per-model system prompt version history."""

import time
import uuid

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.users import UserResponse, Users
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Text, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

####################
# ModelSystemPromptVersion DB Schema
####################


class ModelSystemPromptVersion(Base):
    __tablename__ = 'model_system_prompt_version'

    id = Column(Text, primary_key=True)
    model_id = Column(
        Text,
        ForeignKey('model.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)


class ModelSystemPromptVersionModel(BaseModel):
    id: str
    model_id: str
    content: str
    commit_message: str | None = None
    user_id: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ModelSystemPromptVersionResponse(ModelSystemPromptVersionModel):
    """Response model with user info."""

    user: UserResponse | None = None


class ModelSystemPromptVersionsTable:
    async def create_version(
        self,
        model_id: str,
        content: str,
        user_id: str,
        commit_message: str | None = None,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptVersionModel | None:
        """Create a new version entry for a model system prompt."""
        async with get_async_db_context(db) as db:
            version = ModelSystemPromptVersion(
                id=str(uuid.uuid4()),
                model_id=model_id,
                content=content,
                user_id=user_id,
                commit_message=commit_message,
                created_at=int(time.time()),
            )
            db.add(version)
            await db.commit()
            await db.refresh(version)
            return ModelSystemPromptVersionModel.model_validate(version)

    async def get_versions_by_model_id(
        self,
        model_id: str,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[ModelSystemPromptVersionResponse]:
        """Get all versions for a model, ordered by created_at desc."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptVersion)
                .filter(ModelSystemPromptVersion.model_id == model_id)
                .order_by(ModelSystemPromptVersion.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            entries = result.scalars().all()

            user_ids = list({e.user_id for e in entries})
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            return [
                ModelSystemPromptVersionResponse(
                    **ModelSystemPromptVersionModel.model_validate(entry).model_dump(),
                    user=(users_dict.get(entry.user_id).model_dump() if users_dict.get(entry.user_id) else None),
                )
                for entry in entries
            ]

    async def get_version_by_id(
        self,
        version_id: str,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptVersionModel | None:
        """Get a specific version entry by ID."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptVersion).filter(ModelSystemPromptVersion.id == version_id)
            )
            entry = result.scalars().first()
            if entry:
                return ModelSystemPromptVersionModel.model_validate(entry)
            return None

    async def get_latest_version(
        self,
        model_id: str,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptVersionModel | None:
        """Get the most recent version for a model."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptVersion)
                .filter(ModelSystemPromptVersion.model_id == model_id)
                .order_by(ModelSystemPromptVersion.created_at.desc())
                .limit(1)
            )
            entry = result.scalars().first()
            if entry:
                return ModelSystemPromptVersionModel.model_validate(entry)
            return None

    async def get_version_count(
        self,
        model_id: str,
        db: AsyncSession | None = None,
    ) -> int:
        """Get the number of versions for a model."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(func.count())
                .select_from(ModelSystemPromptVersion)
                .filter(ModelSystemPromptVersion.model_id == model_id)
            )
            return result.scalar()

    async def delete_versions_by_model_id(
        self,
        model_id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Delete all versions for a model."""
        async with get_async_db_context(db) as db:
            await db.execute(delete(ModelSystemPromptVersion).filter(ModelSystemPromptVersion.model_id == model_id))
            await db.commit()
            return True

    async def delete_version(
        self,
        version_id: str,
        model_id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Delete a version entry scoped to the authorized model."""
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ModelSystemPromptVersion).filter_by(id=version_id, model_id=model_id))
            entry = result.scalars().first()
            if not entry:
                return False

            await db.delete(entry)
            await db.commit()
            return True


ModelSystemPromptVersions = ModelSystemPromptVersionsTable()
