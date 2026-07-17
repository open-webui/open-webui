from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.integrations.langfuse.connections import get_connection_by_id
from open_webui.integrations.langfuse.provider import LangfusePromptError, LangfusePromptProvider
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
    SystemPromptSource,
)
from open_webui.models.model_system_prompt_version import (
    ModelSystemPromptVersionModel,
    ModelSystemPromptVersionResponse,
    ModelSystemPromptVersions,
)
from open_webui.models.models import ModelForm, ModelModel, ModelParams, Models
from open_webui.routers.models import is_valid_model_id
from open_webui.utils.auth import get_verified_user
from open_webui.utils.system_prompt import refresh_langfuse_system_prompt
from open_webui.utils.system_prompt_cache import invalidate_system_prompt_cache
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

PAGE_SIZE = 20


class CreateSystemPromptVersionForm(BaseModel):
    content: str
    commit_message: Optional[str] = None
    set_active: bool = True


class SetActiveSystemPromptVersionForm(BaseModel):
    version_id: str


class PatchSystemPromptBindingForm(BaseModel):
    source: SystemPromptSource | None = None
    connection_id: str | None = None
    external_name: str | None = None
    external_label: str | None = None
    external_version: str | None = None
    cache_ttl_seconds: int | None = None


class LangfusePromptPreviewForm(BaseModel):
    connection_id: str | None = None
    external_name: str | None = None
    external_label: str | None = None
    external_version: str | None = None


class LangfusePromptActionResponse(BaseModel):
    content: str
    prompt_name: str | None = None
    prompt_version: str | None = None
    source: Literal['langfuse'] = 'langfuse'


class DetachSystemPromptResponse(BaseModel):
    binding: ModelSystemPromptBindingModel
    version: ModelSystemPromptVersionResponse


async def _get_model_or_404(model_id: str, db: AsyncSession) -> ModelModel:
    if not is_valid_model_id(model_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    model = await Models.get_model_by_id(model_id, db=db)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return model


async def _has_model_read_access(model: ModelModel, user, db: AsyncSession) -> bool:
    return (
        user.role == 'admin'
        or model.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='model',
            resource_id=model.id,
            permission='read',
            db=db,
        )
    )


async def _has_model_write_access(model: ModelModel, user, db: AsyncSession) -> bool:
    return (
        user.role == 'admin'
        or model.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='model',
            resource_id=model.id,
            permission='write',
            db=db,
        )
    )


async def _require_model_read_access(model: ModelModel, user, db: AsyncSession) -> None:
    if not await _has_model_read_access(model, user, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


async def _require_model_write_access(model: ModelModel, user, db: AsyncSession) -> None:
    if not await _has_model_write_access(model, user, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


async def _mirror_params_system(
    model: ModelModel,
    content: str,
    db: AsyncSession,
) -> None:
    params_data = model.params.model_dump()
    params_data['system'] = content
    form = ModelForm(
        id=model.id,
        name=model.name,
        base_model_id=model.base_model_id,
        meta=model.meta,
        params=ModelParams(**params_data),
        is_active=model.is_active,
    )
    updated = await Models.update_model_by_id(model.id, form, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


async def _ensure_local_binding(
    model_id: str,
    active_version_id: str,
    db: AsyncSession,
) -> ModelSystemPromptBindingModel:
    binding = await ModelSystemPromptBindings.get_by_model_id(model_id, db=db)
    if binding:
        await ModelSystemPromptBindings.update_source(model_id, 'local', db=db)
        updated = await ModelSystemPromptBindings.update_active_version(
            model_id,
            active_version_id,
            db=db,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return updated

    return await ModelSystemPromptBindings.upsert(
        model_id=model_id,
        source='local',
        active_version_id=active_version_id,
        db=db,
    )


async def _get_version_for_model_or_404(
    model_id: str,
    version_id: str,
    db: AsyncSession,
) -> ModelSystemPromptVersionModel:
    version = await ModelSystemPromptVersions.get_version_by_id(version_id, db=db)
    if not version or version.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return version


def _resolve_langfuse_binding_fields(
    binding: ModelSystemPromptBindingModel | None,
    form_data: LangfusePromptPreviewForm,
) -> tuple[str, str, str | None, str | None]:
    connection_id = form_data.connection_id or (binding.connection_id if binding else None)
    external_name = form_data.external_name or (binding.external_name if binding else None)
    external_label = (
        form_data.external_label
        if form_data.external_label is not None
        else (binding.external_label if binding else None)
    )
    external_version = (
        form_data.external_version
        if form_data.external_version is not None
        else (binding.external_version if binding else None)
    )

    if not connection_id or not external_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Langfuse connection_id and external_name are required',
        )

    return connection_id, external_name, external_label, external_version


async def _preview_langfuse_prompt(
    connection_id: str,
    external_name: str,
    *,
    external_label: str | None,
    external_version: str | None,
) -> LangfusePromptActionResponse:
    connection = await get_connection_by_id(connection_id)
    if not connection or not connection.get('enabled', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Langfuse connection is missing or disabled',
        )

    provider = LangfusePromptProvider()
    try:
        result = await provider.fetch_prompt(
            connection,
            external_name,
            label=external_label,
            version=external_version,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    version = str(result.version) if result.version is not None else None
    return LangfusePromptActionResponse(
        content=result.content,
        prompt_name=result.name,
        prompt_version=version,
    )


############################
# Model System Prompt Endpoints
############################


@router.get('/system-prompt/binding', response_model=ModelSystemPromptBindingModel | None)
async def get_model_system_prompt_binding(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the system prompt binding for a model."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)
    return await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)


@router.get('/system-prompt/history', response_model=list[ModelSystemPromptVersionResponse])
async def get_model_system_prompt_history(
    id: str,
    page: int = 0,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get version history for a model system prompt."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)

    return await ModelSystemPromptVersions.get_versions_by_model_id(
        model.id,
        limit=PAGE_SIZE,
        offset=page * PAGE_SIZE,
        db=db,
    )


@router.get('/system-prompt/history/{version_id}', response_model=ModelSystemPromptVersionModel)
async def get_model_system_prompt_history_entry(
    version_id: str,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific system prompt version."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)
    return await _get_version_for_model_or_404(model.id, version_id, db)


@router.post('/system-prompt/versions', response_model=ModelSystemPromptVersionResponse)
async def create_model_system_prompt_version(
    id: str,
    form_data: CreateSystemPromptVersionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new local system prompt version."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    version = await ModelSystemPromptVersions.create_version(
        model_id=model.id,
        content=form_data.content,
        user_id=user.id,
        commit_message=form_data.commit_message,
        db=db,
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    if form_data.set_active:
        await _ensure_local_binding(model.id, version.id, db)
        await _mirror_params_system(model, form_data.content, db)
        invalidate_system_prompt_cache(model.id)

    return ModelSystemPromptVersionResponse(**version.model_dump(), user=None)


@router.post('/system-prompt/active', response_model=ModelSystemPromptBindingModel)
async def set_active_model_system_prompt_version(
    id: str,
    form_data: SetActiveSystemPromptVersionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Set the active local system prompt version."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    version = await _get_version_for_model_or_404(model.id, form_data.version_id, db)
    binding = await _ensure_local_binding(model.id, version.id, db)
    await _mirror_params_system(model, version.content, db)
    invalidate_system_prompt_cache(model.id)
    return binding


@router.delete('/system-prompt/history/{version_id}', response_model=bool)
async def delete_model_system_prompt_history_entry(
    version_id: str,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a system prompt version. Cannot delete the active version."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    if binding and binding.active_version_id == version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot delete the active production version',
        )

    version = await ModelSystemPromptVersions.get_version_by_id(version_id, db=db)
    if not version or version.model_id != model.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    success = await ModelSystemPromptVersions.delete_version(version_id, model.id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return success


@router.patch('/system-prompt/binding', response_model=ModelSystemPromptBindingModel)
async def patch_model_system_prompt_binding(
    id: str,
    form_data: PatchSystemPromptBindingForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update system prompt binding Langfuse fields and source without fetching."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    source = form_data.source or (binding.source if binding else 'local')
    active_version_id = binding.active_version_id if binding else None

    updated = await ModelSystemPromptBindings.upsert(
        model_id=model.id,
        source=source,
        active_version_id=active_version_id,
        connection_id=form_data.connection_id
        if form_data.connection_id is not None
        else (binding.connection_id if binding else None),
        external_name=form_data.external_name
        if form_data.external_name is not None
        else (binding.external_name if binding else None),
        external_label=form_data.external_label
        if form_data.external_label is not None
        else (binding.external_label if binding else None),
        external_version=form_data.external_version
        if form_data.external_version is not None
        else (binding.external_version if binding else None),
        cached_content=binding.cached_content if binding else None,
        cached_version=binding.cached_version if binding else None,
        cached_at=binding.cached_at if binding else None,
        cache_ttl_seconds=form_data.cache_ttl_seconds
        if form_data.cache_ttl_seconds is not None
        else (binding.cache_ttl_seconds if binding else None),
        db=db,
    )
    invalidate_system_prompt_cache(model.id)
    return updated


@router.post('/system-prompt/langfuse/sync', response_model=LangfusePromptActionResponse)
async def sync_langfuse_system_prompt(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Force refresh the Langfuse prompt cache for a model."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    if not binding or binding.source != 'langfuse':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Model is not bound to a Langfuse system prompt',
        )

    invalidate_system_prompt_cache(model.id)
    try:
        result = await refresh_langfuse_system_prompt(
            model.id,
            binding,
            persist=True,
            db=db,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return LangfusePromptActionResponse(**result)


@router.post('/system-prompt/langfuse/preview', response_model=LangfusePromptActionResponse)
async def preview_langfuse_system_prompt(
    id: str,
    form_data: LangfusePromptPreviewForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Dry-run fetch of a Langfuse prompt without persisting cache fields."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    connection_id, external_name, external_label, external_version = _resolve_langfuse_binding_fields(
        binding,
        form_data,
    )
    return await _preview_langfuse_prompt(
        connection_id,
        external_name,
        external_label=external_label,
        external_version=external_version,
    )


@router.post('/system-prompt/detach', response_model=DetachSystemPromptResponse)
async def detach_langfuse_system_prompt(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Copy cached Langfuse content into a new local version and mirror params.system."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    if not binding or binding.source != 'langfuse':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Model is not bound to a Langfuse system prompt',
        )
    if not binding.cached_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No cached Langfuse content available to detach',
        )

    version = await ModelSystemPromptVersions.create_version(
        model_id=model.id,
        content=binding.cached_content,
        user_id=user.id,
        commit_message='Detached from Langfuse',
        db=db,
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    updated_binding = await ModelSystemPromptBindings.upsert(
        model_id=model.id,
        source='local',
        active_version_id=version.id,
        connection_id=None,
        external_name=None,
        external_label=None,
        external_version=None,
        cached_content=None,
        cached_version=None,
        cached_at=None,
        cache_ttl_seconds=None,
        db=db,
    )
    await _mirror_params_system(model, binding.cached_content, db)
    invalidate_system_prompt_cache(model.id)

    return DetachSystemPromptResponse(
        binding=updated_binding,
        version=ModelSystemPromptVersionResponse(**version.model_dump(), user=None),
    )
