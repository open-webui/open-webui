from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.integrations.langfuse.connections import (
    get_connection_by_id,
    list_enabled_connections,
    redact_langfuse_connections_for_response,
)
from open_webui.integrations.langfuse.provider import LangfusePromptError, LangfusePromptProvider
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.model_system_prompt_binding import (
    BindingVersionConflictError,
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

LANGFUSE_IDENTITY_FIELDS = (
    'connection_id',
    'external_name',
    'external_label',
    'external_version',
)


class CreateSystemPromptVersionForm(BaseModel):
    content: str
    commit_message: str | None = None
    set_active: bool = True
    expected_updated_at: int | None = None


class SetActiveSystemPromptVersionForm(BaseModel):
    version_id: str
    expected_updated_at: int | None = None


class PatchSystemPromptBindingForm(BaseModel):
    source: SystemPromptSource | None = None
    connection_id: str | None = None
    external_name: str | None = None
    external_label: str | None = None
    external_version: str | None = None
    cache_ttl_seconds: int | None = None
    expected_updated_at: int | None = None


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


def _cleared_langfuse_binding_fields() -> dict[str, None]:
    return {
        'connection_id': None,
        'external_name': None,
        'external_label': None,
        'external_version': None,
        'cached_content': None,
        'cached_version': None,
        'cached_at': None,
        'cache_ttl_seconds': None,
    }


async def _ensure_local_binding(
    model_id: str,
    active_version_id: str,
    db: AsyncSession,
    *,
    expected_updated_at: int | None = None,
) -> ModelSystemPromptBindingModel:
    return await ModelSystemPromptBindings.upsert(
        model_id=model_id,
        source='local',
        active_version_id=active_version_id,
        expected_updated_at=expected_updated_at,
        **_cleared_langfuse_binding_fields(),
        db=db,
    )


def _raise_binding_version_conflict(exc: BindingVersionConflictError) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            'message': 'System prompt binding was modified by another request',
            'current_updated_at': exc.current_updated_at,
        },
    ) from exc


async def _get_enabled_langfuse_connection_or_404(connection_id: str) -> dict[str, Any]:
    connection = await get_connection_by_id(connection_id)
    if not connection or not connection.get('enabled', True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Langfuse connection not found',
        )
    return connection


async def _authorize_langfuse_connection_for_model(
    model: ModelModel,
    user,
    db: AsyncSession,
    connection_id: str,
    binding: ModelSystemPromptBindingModel | None,
    *,
    configure: bool = False,
) -> None:
    """Authorize Langfuse connection access in model context.

    Read-only users may only use the model's bound connection (or admin).
    Write holders may browse any enabled connection while configuring.
    """
    if user.role == 'admin':
        return

    if configure and await _has_model_write_access(model, user, db):
        return

    if binding and binding.connection_id == connection_id:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


async def _require_bound_langfuse_identity_for_readonly(
    model: ModelModel,
    user,
    db: AsyncSession,
    binding: ModelSystemPromptBindingModel | None,
    *,
    external_name: str | None,
    external_label: str | None,
    external_version: str | None,
) -> None:
    if user.role == 'admin' or await _has_model_write_access(model, user, db):
        return

    if not binding or binding.source != 'langfuse':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if external_name != binding.external_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    if external_label != binding.external_label:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    if external_version != binding.external_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


def _assert_langfuse_label_xor_version(
    external_label: str | None,
    external_version: str | None,
) -> None:
    if external_label and external_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Specify external_label or external_version, not both',
        )


def _parse_if_match_updated_at(if_match: str | None) -> int | None:
    if not if_match or not isinstance(if_match, str):
        return None
    token = if_match.strip().strip('"')
    if not token.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid If-Match header',
        )
    return int(token)


def _resolve_expected_updated_at(
    form_expected: int | None,
    if_match: str | None,
) -> int | None:
    header_expected = _parse_if_match_updated_at(if_match)
    if form_expected is not None and header_expected is not None:
        if form_expected != header_expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='expected_updated_at conflicts with If-Match',
            )
    return form_expected if form_expected is not None else header_expected


def _langfuse_identity_changed(
    binding: ModelSystemPromptBindingModel | None,
    *,
    connection_id: str | None,
    external_name: str | None,
    external_label: str | None,
    external_version: str | None,
) -> bool:
    if not binding:
        return True

    return (
        connection_id != binding.connection_id
        or external_name != binding.external_name
        or external_label != binding.external_label
        or external_version != binding.external_version
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

    _assert_langfuse_label_xor_version(external_label, external_version)

    return connection_id, external_name, external_label, external_version


async def _preview_langfuse_prompt(
    connection_id: str,
    external_name: str,
    *,
    external_label: str | None,
    external_version: str | None,
) -> LangfusePromptActionResponse:
    connection = await _get_enabled_langfuse_connection_or_404(connection_id)

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
    if_match: str | None = Header(default=None, alias='If-Match'),
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
        expected_updated_at = _resolve_expected_updated_at(
            form_data.expected_updated_at,
            if_match,
        )
        try:
            await _ensure_local_binding(
                model.id,
                version.id,
                db,
                expected_updated_at=expected_updated_at,
            )
        except BindingVersionConflictError as exc:
            _raise_binding_version_conflict(exc)
        await _mirror_params_system(model, form_data.content, db)
        invalidate_system_prompt_cache(model.id)

    return ModelSystemPromptVersionResponse(**version.model_dump(), user=None)


@router.post('/system-prompt/active', response_model=ModelSystemPromptBindingModel)
async def set_active_model_system_prompt_version(
    id: str,
    form_data: SetActiveSystemPromptVersionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Set the active local system prompt version."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    version = await _get_version_for_model_or_404(model.id, form_data.version_id, db)
    expected_updated_at = _resolve_expected_updated_at(
        form_data.expected_updated_at,
        if_match,
    )
    try:
        binding = await _ensure_local_binding(
            model.id,
            version.id,
            db,
            expected_updated_at=expected_updated_at,
        )
    except BindingVersionConflictError as exc:
        _raise_binding_version_conflict(exc)
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

    invalidate_system_prompt_cache(model.id)
    return success


@router.patch('/system-prompt/binding', response_model=ModelSystemPromptBindingModel)
async def patch_model_system_prompt_binding(
    id: str,
    form_data: PatchSystemPromptBindingForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    """Update system prompt binding Langfuse fields and source without fetching."""
    model = await _get_model_or_404(id, db)
    await _require_model_write_access(model, user, db)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    expected_updated_at = _resolve_expected_updated_at(
        form_data.expected_updated_at,
        if_match,
    )
    source = form_data.source or (binding.source if binding else 'local')
    active_version_id = binding.active_version_id if binding else None

    if source == 'local':
        try:
            updated = await ModelSystemPromptBindings.upsert(
                model_id=model.id,
                source='local',
                active_version_id=active_version_id,
                expected_updated_at=expected_updated_at,
                **_cleared_langfuse_binding_fields(),
                db=db,
            )
        except BindingVersionConflictError as exc:
            _raise_binding_version_conflict(exc)
        invalidate_system_prompt_cache(model.id)
        return updated

    connection_id = (
        form_data.connection_id if form_data.connection_id is not None else (binding.connection_id if binding else None)
    )
    external_name = (
        form_data.external_name if form_data.external_name is not None else (binding.external_name if binding else None)
    )
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
    cache_ttl_seconds = (
        form_data.cache_ttl_seconds
        if form_data.cache_ttl_seconds is not None
        else (binding.cache_ttl_seconds if binding else None)
    )

    _assert_langfuse_label_xor_version(external_label, external_version)

    if connection_id:
        await _authorize_langfuse_connection_for_model(
            model,
            user,
            db,
            connection_id,
            binding,
            configure=True,
        )

    identity_changed = _langfuse_identity_changed(
        binding,
        connection_id=connection_id,
        external_name=external_name,
        external_label=external_label,
        external_version=external_version,
    )

    try:
        updated = await ModelSystemPromptBindings.upsert(
            model_id=model.id,
            source=source,
            active_version_id=active_version_id,
            connection_id=connection_id,
            external_name=external_name,
            external_label=external_label,
            external_version=external_version,
            cached_content=None if identity_changed else (binding.cached_content if binding else None),
            cached_version=None if identity_changed else (binding.cached_version if binding else None),
            cached_at=None if identity_changed else (binding.cached_at if binding else None),
            cache_ttl_seconds=cache_ttl_seconds,
            expected_updated_at=expected_updated_at,
            db=db,
        )
    except BindingVersionConflictError as exc:
        _raise_binding_version_conflict(exc)
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
    has_write = await _has_model_write_access(model, user, db)
    await _authorize_langfuse_connection_for_model(
        model,
        user,
        db,
        connection_id,
        binding,
        configure=has_write,
    )
    await _require_bound_langfuse_identity_for_readonly(
        model,
        user,
        db,
        binding,
        external_name=external_name,
        external_label=external_label,
        external_version=external_version,
    )
    return await _preview_langfuse_prompt(
        connection_id,
        external_name,
        external_label=external_label,
        external_version=external_version,
    )


@router.get('/system-prompt/langfuse/connections')
async def list_model_langfuse_connections(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List Langfuse connections visible in the model editor (redacted)."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)

    if user.role == 'admin' or await _has_model_write_access(model, user, db):
        connections = await list_enabled_connections()
    else:
        binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
        if binding and binding.connection_id:
            connection = await get_connection_by_id(binding.connection_id)
            if connection and connection.get('enabled', True):
                connections = [connection]
            else:
                connections = []
        else:
            connections = []

    return {
        'connections': redact_langfuse_connections_for_response(connections),
    }


@router.get('/system-prompt/langfuse/prompts')
async def list_model_langfuse_prompts(
    id: str,
    connection_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    name: str | None = None,
    label: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Proxy Langfuse prompt list scoped to model access."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)

    _assert_langfuse_label_xor_version(label, None)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    has_write = await _has_model_write_access(model, user, db)
    if user.role != 'admin' and not has_write:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    await _authorize_langfuse_connection_for_model(
        model,
        user,
        db,
        connection_id,
        binding,
        configure=True,
    )

    connection = await _get_enabled_langfuse_connection_or_404(connection_id)
    provider = LangfusePromptProvider()
    try:
        return await provider.list_prompts(
            connection,
            page=page,
            limit=limit,
            name=name,
            label=label,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get('/system-prompt/langfuse/prompts/{prompt_name:path}')
async def get_model_langfuse_prompt(
    id: str,
    prompt_name: str,
    connection_id: str,
    label: str | None = None,
    version: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Proxy Langfuse prompt fetch scoped to model access."""
    model = await _get_model_or_404(id, db)
    await _require_model_read_access(model, user, db)

    _assert_langfuse_label_xor_version(label, version)

    binding = await ModelSystemPromptBindings.get_by_model_id(model.id, db=db)
    has_write = await _has_model_write_access(model, user, db)
    await _authorize_langfuse_connection_for_model(
        model,
        user,
        db,
        connection_id,
        binding,
        configure=has_write,
    )

    fetch_label = label if label is not None else (binding.external_label if binding else None)
    fetch_version = version if version is not None else (binding.external_version if binding else None)
    await _require_bound_langfuse_identity_for_readonly(
        model,
        user,
        db,
        binding,
        external_name=prompt_name,
        external_label=fetch_label,
        external_version=fetch_version,
    )

    connection = await _get_enabled_langfuse_connection_or_404(connection_id)
    provider = LangfusePromptProvider()
    try:
        return await provider.get_prompt(
            connection,
            prompt_name,
            label=fetch_label,
            version=fetch_version,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
