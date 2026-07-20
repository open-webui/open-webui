"""Auto-version local system prompts when params.system changes on model save."""

from __future__ import annotations

import logging

from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
)
from open_webui.models.model_system_prompt_version import (
    ModelSystemPromptVersionModel,
    ModelSystemPromptVersions,
)
from open_webui.models.models import ModelParams
from open_webui.utils.system_prompt_cache import invalidate_system_prompt_cache
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def normalize_system_content(value: str | None) -> str | None:
    """Match ModelEditor: empty/whitespace-only strings become None."""
    if value is None:
        return None
    if value.strip() == '':
        return None
    return value


def get_params_system(params: ModelParams | None) -> str | None:
    if not params:
        return None
    system = params.model_dump().get('system')
    return system if isinstance(system, str) or system is None else str(system)


def system_content_for_version(value: str | None) -> str:
    normalized = normalize_system_content(value)
    return normalized if normalized is not None else ''


async def _ensure_local_binding(
    model_id: str,
    active_version_id: str,
    db: AsyncSession,
) -> ModelSystemPromptBindingModel | None:
    binding = await ModelSystemPromptBindings.get_by_model_id(model_id, db=db)
    if binding:
        await ModelSystemPromptBindings.update_source(model_id, 'local', db=db)
        return await ModelSystemPromptBindings.update_active_version(
            model_id,
            active_version_id,
            db=db,
        )

    return await ModelSystemPromptBindings.upsert(
        model_id=model_id,
        source='local',
        active_version_id=active_version_id,
        db=db,
    )


async def maybe_auto_version_from_params_system(
    model_id: str,
    previous_system: str | None,
    new_system: str | None,
    user_id: str,
    db: AsyncSession,
    commit_message: str | None = None,
) -> ModelSystemPromptVersionModel | None:
    """Create a local version when params.system changes under local/no binding.

    Caller must have already persisted params.system. Does not mirror back to params.
    """
    prev = normalize_system_content(previous_system)
    new = normalize_system_content(new_system)
    if prev == new:
        return None

    binding = await ModelSystemPromptBindings.get_by_model_id(model_id, db=db)
    if binding and binding.source == 'langfuse':
        return None

    if binding and binding.active_version_id:
        active = await ModelSystemPromptVersions.get_version_by_id(
            binding.active_version_id,
            db=db,
        )
        if active and normalize_system_content(active.content) == new:
            return None

    version = await ModelSystemPromptVersions.create_version(
        model_id=model_id,
        content=system_content_for_version(new_system),
        user_id=user_id,
        commit_message=commit_message,
        db=db,
    )
    if not version:
        log.warning('maybe_auto_version_from_params_system: failed to create version for %s', model_id)
        return None

    binding_result = await _ensure_local_binding(model_id, version.id, db=db)
    if not binding_result:
        log.warning(
            'maybe_auto_version_from_params_system: failed to set local binding for %s',
            model_id,
        )
        return version

    invalidate_system_prompt_cache(model_id)
    return version
