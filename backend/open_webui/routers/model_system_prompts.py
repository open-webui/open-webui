from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
)
from open_webui.models.model_system_prompt_version import (
    ModelSystemPromptVersionModel,
    ModelSystemPromptVersionResponse,
    ModelSystemPromptVersions,
)
from open_webui.models.models import ModelForm, ModelModel, ModelParams, Models
from open_webui.routers.models import is_valid_model_id
from open_webui.utils.auth import get_verified_user
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
