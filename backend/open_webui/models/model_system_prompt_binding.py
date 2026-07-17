"""Per-model system prompt source binding and Langfuse cache."""

from typing import Literal, Optional

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text
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


class ModelSystemPromptBindingModel(BaseModel):
    model_id: str
    source: SystemPromptSource
    active_version_id: Optional[str] = None
    connection_id: Optional[str] = None
    external_name: Optional[str] = None
    external_label: Optional[str] = None
    external_version: Optional[str] = None
    cached_content: Optional[str] = None
    cached_version: Optional[str] = None
    cached_at: Optional[int] = None
    cache_ttl_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ModelSystemPromptBindingsTable:
    async def get_by_model_id(
        self,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptBindingModel]:
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
        active_version_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        external_name: Optional[str] = None,
        external_label: Optional[str] = None,
        external_version: Optional[str] = None,
        cached_content: Optional[str] = None,
        cached_version: Optional[str] = None,
        cached_at: Optional[int] = None,
        cache_ttl_seconds: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> ModelSystemPromptBindingModel:
        """Create or replace binding fields for a model."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
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
            else:
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
                )
                db.add(binding)

            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_active_version(
        self,
        model_id: str,
        active_version_id: Optional[str],
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptBindingModel]:
        """Update the active local version pointer."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.active_version_id = active_version_id
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_source(
        self,
        model_id: str,
        source: SystemPromptSource,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptBindingModel]:
        """Update the prompt source mode."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.source = source
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)

    async def update_cache_fields(
        self,
        model_id: str,
        *,
        cached_content: Optional[str] = None,
        cached_version: Optional[str] = None,
        cached_at: Optional[int] = None,
        cache_ttl_seconds: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptBindingModel]:
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
        connection_id: Optional[str] = None,
        external_name: Optional[str] = None,
        external_label: Optional[str] = None,
        external_version: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptBindingModel]:
        """Update Langfuse external reference fields on an existing binding."""
        async with get_async_db_context(db) as db:
            binding = await db.get(ModelSystemPromptBinding, model_id)
            if not binding:
                return None

            binding.connection_id = connection_id
            binding.external_name = external_name
            binding.external_label = external_label
            binding.external_version = external_version
            await db.commit()
            await db.refresh(binding)
            return ModelSystemPromptBindingModel.model_validate(binding)


ModelSystemPromptBindings = ModelSystemPromptBindingsTable()
