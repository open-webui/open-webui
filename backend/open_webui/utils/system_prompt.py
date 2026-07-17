import logging
import time

from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
)
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions
from open_webui.utils.payload import resolve_system_prompt

log = logging.getLogger(__name__)

DEFAULT_LANGFUSE_CACHE_TTL_SECONDS = 300


def _get_params_system_mirror(model_info) -> str | None:
    if model_info.params:
        return model_info.params.model_dump().get('system')
    return None


def _is_langfuse_cache_warm(binding: ModelSystemPromptBindingModel) -> bool:
    if not binding.cached_content:
        return False
    if binding.cached_at is None:
        return True

    ttl = binding.cache_ttl_seconds or DEFAULT_LANGFUSE_CACHE_TTL_SECONDS
    return (time.time() - binding.cached_at) < ttl


async def _resolve_raw_system_prompt(model_info) -> str | None:
    mirror = _get_params_system_mirror(model_info)

    try:
        binding = await ModelSystemPromptBindings.get_by_model_id(model_info.id)
    except Exception:
        log.exception('Failed to load system prompt binding for model %s', model_info.id)
        return mirror

    if not binding:
        return mirror

    if binding.source == 'local':
        if binding.active_version_id:
            try:
                version = await ModelSystemPromptVersions.get_version_by_id(binding.active_version_id)
            except Exception:
                log.exception(
                    'Failed to load active system prompt version %s for model %s',
                    binding.active_version_id,
                    model_info.id,
                )
                return mirror

            if version and version.content:
                return version.content

        return mirror

    if binding.source == 'langfuse':
        if _is_langfuse_cache_warm(binding):
            return binding.cached_content

        # Phase 2: fetch from Langfuse when cache is stale or missing.
        if binding.cached_content:
            return binding.cached_content

        return mirror

    log.warning(
        'Unknown system prompt source %r for model %s; falling back to params.system mirror',
        binding.source,
        model_info.id,
    )
    return mirror


async def resolve_model_system_prompt(
    model_info,  # ModelModel | None
    metadata: dict | None,
    user,
    *,
    bypass: bool = False,
) -> str:
    if bypass or model_info is None:
        return ''

    raw = await _resolve_raw_system_prompt(model_info)
    return await resolve_system_prompt(raw, metadata, user)
