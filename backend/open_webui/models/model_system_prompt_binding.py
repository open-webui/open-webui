"""Per-model system prompt source binding and Langfuse cache."""

import time
from typing import Literal

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

SystemPromptSource = Literal['local', 'langfuse']

####################
# ModelSystemPromptBinding DB Schema
####################


class ModelSystemPromptBinding(Base):
    __tablename__ = 'model_system_prompt_binding'

    model_id = Column(
        Text,
        ForeignKey('model.id', ondelete='CASCADE'),
        primary_key=True,
    )
    source = Column(Text, nullable=False)
    active_version_id = Column(
        Text,
        ForeignKey('model_system_prompt_version.id', ondelete='SET NULL'),
        nullable=True,
    )
    connection_id = Column(Text, nullable=True)
    external_name = Column(Text, nullable=True)
    external_label = Column(Text, nullable=True)
    external_version = Column(Text, nullable=True)
    cached_content = Column(Text, nullable=True)
    cached_version = Column(Text, nullable=True)
    cached_at = Column(BigInteger, nullable=True)
    cache_ttl_seconds = Column(Integer, nullable=True)
    updated_at = Column(BigInteger, nullable=True)


class ModelSystemPromptBindingModel(BaseModel):
    model_id: str
    source: SystemPromptSource
    active_version_id: str | None = None
    connection_id: str | None = None
    external_name: str | None = None
    external_label: str | None = None
    external_version: str | None = None
    cached_content: str | None = None
    cached_version: str | None = None
    cached_at: int | None = None
    cache_ttl_seconds: int | None = None
    updated_at: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ModelSystemPromptBindingsTable:
    async def count_by_connection_id(
        self,
        connection_id: str,
        db: AsyncSession | None = None,
    ) -> int:
        """Count langfuse bindings referencing a connection."""
        async with get_async_db_context(db) as db:
            stmt = (
                select(func.count())
                .select_from(ModelSystemPromptBinding)
                .where(
                    ModelSystemPromptBinding.connection_id == connection_id,
                    ModelSystemPromptBinding.source == 'langfuse',
                )
            )
            result = await db.execute(stmt)
            return int(result.scalar_one())

    async def get_by_model_id(
        self,
        model_id: str,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel | None:
        """Get the binding for a model, if any."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if binding:
                return ModelSystemPromptBindingModel.model_validate(binding)
            return None

    async def upsert(
        self,
        model_id: str,
        source: SystemPromptSource,
        active_version_id: str | None = None,
        connection_id: str | None = None,
        external_name: str | None = None,
        external_label: str | None = None,
        external_version: str | None = None,
        cached_content: str | None = None,
        cached_version: str | None = None,
        cached_at: int | None = None,
        cache_ttl_seconds: int | None = None,
        expected_updated_at: int | None = None,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel:
        """Create or replace binding fields for a model."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if binding and expected_updated_at is not None:
                current = binding.updated_at
                if current is None or current != expected_updated_at:
                    raise BindingVersionConflictError(model_id, current)

            now = int(time.time())
            if binding:
                binding.source = source
                binding.active_version_id = active_version_id
                binding.connection_id = connection_id
                binding.external_name = external_name
                binding.external_label = external_label
                binding.external_version = external_version
                binding.cached_content = cached_content
                binding.cached_version = cached_version
                binding.cached_at = cached_at
                binding.cache_ttl_seconds = cache_ttl_seconds
                binding.updated_at = now
            else:
                if expected_updated_at is not None:
                    raise BindingVersionConflictError(model_id, None)
                binding = ModelSystemPromptBinding(
                    model_id=model_id,
                    source=source,
                    active_version_id=active_version_id,
                    connection_id=connection_id,
                    external_name=external_name,
                    external_label=external_label,
                    external_version=external_version,
                    cached_content=cached_content,
                    cached_version=cached_version,
                    cached_at=cached_at,
                    cache_ttl_seconds=cache_ttl_seconds,
                    updated_at=now,
                )
                db.add(binding)

            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_active_version(
        self,
        model_id: str,
        active_version_id: str | None,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel | None:
        """Update the active local version pointer."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.active_version_id = active_version_id
            binding.updated_at = int(time.time())
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_source(
        self,
        model_id: str,
        source: SystemPromptSource,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel | None:
        """Update the prompt source mode."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.source = source
            binding.updated_at = int(time.time())
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_cache_fields(
        self,
        model_id: str,
        *,
        cached_content: str | None = None,
        cached_version: str | None = None,
        cached_at: int | None = None,
        cache_ttl_seconds: int | None = None,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel | None:
        """Update Langfuse cache fields on an existing binding."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.cached_content = cached_content
            binding.cached_version = cached_version
            binding.cached_at = cached_at
            binding.cache_ttl_seconds = cache_ttl_seconds
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_external_fields(
        self,
        model_id: str,
        *,
        connection_id: str | None = None,
        external_name: str | None = None,
        external_label: str | None = None,
        external_version: str | None = None,
        db: AsyncSession | None = None,
    ) -> ModelSystemPromptBindingModel | None:
        """Update Langfuse external reference fields on an existing binding."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.connection_id = connection_id
            binding.external_name = external_name
            binding.external_label = external_label
            binding.external_version = external_version
            binding.updated_at = int(time.time())
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)


class BindingVersionConflictError(Exception):
    def __init__(self, model_id: str, current_updated_at: int | None) -> None:
        self.model_id = model_id
        self.current_updated_at = current_updated_at
        super().__init__(model_id)


ModelSystemPromptBindings = ModelSystemPromptBindingsTable()
