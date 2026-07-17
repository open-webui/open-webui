import logging
import time

from open_webui.integrations.langfuse.connections import get_connection_by_id
from open_webui.integrations.langfuse.provider import LangfusePromptError, LangfusePromptProvider
from open_webui.models.config import Config
from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
)
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions
from open_webui.utils.payload import resolve_system_prompt
from open_webui.utils.system_prompt_cache import (
    get_cached_system_prompt,
    invalidate_system_prompt_cache,
    set_cached_system_prompt,
)

log = logging.getLogger(__name__)

DEFAULT_LANGFUSE_CACHE_TTL_SECONDS = 300


def _get_params_system_mirror(model_info) -> str | None:
    if model_info.params:
        return model_info.params.model_dump().get('system')
    return None


async def _get_default_cache_ttl_seconds() -> int:
    ttl = await Config.get('langfuse.prompt_cache_ttl')
    return ttl if ttl is not None else DEFAULT_LANGFUSE_CACHE_TTL_SECONDS


def _binding_cache_ttl_seconds(
    binding: ModelSystemPromptBindingModel,
    default_ttl: int,
) -> int:
    return binding.cache_ttl_seconds or default_ttl


def _is_langfuse_cache_warm(
    binding: ModelSystemPromptBindingModel,
    *,
    default_ttl: int,
) -> bool:
    if not binding.cached_content:
        return False
    if binding.cached_at is None:
        return True

    ttl = _binding_cache_ttl_seconds(binding, default_ttl)
    return (time.time() - binding.cached_at) < ttl


def _langfuse_metadata(
    binding: ModelSystemPromptBindingModel,
    *,
    prompt_version: str | None = None,
) -> dict[str, str | None]:
    return {
        'langfuse_prompt_name': binding.external_name,
        'langfuse_prompt_version': prompt_version or binding.cached_version,
    }


async def _fetch_langfuse_prompt_content(
    binding: ModelSystemPromptBindingModel,
) -> tuple[str, str | None]:
    if not binding.connection_id or not binding.external_name:
        raise LangfusePromptError('Langfuse binding is missing connection_id or external_name')

    connection = await get_connection_by_id(binding.connection_id)
    if not connection or not connection.get('enabled', True):
        raise LangfusePromptError('Langfuse connection is missing or disabled')

    provider = LangfusePromptProvider()
    result = await provider.fetch_prompt(
        connection,
        binding.external_name,
        label=binding.external_label,
        version=binding.external_version,
    )
    version = str(result.version) if result.version is not None else None
    return result.content, version


async def refresh_langfuse_system_prompt(
    model_id: str,
    binding: ModelSystemPromptBindingModel,
    *,
    persist: bool = True,
    db=None,
) -> dict[str, str | None]:
    """Fetch a Langfuse prompt for a binding, optionally persisting cache fields."""
    default_ttl = await _get_default_cache_ttl_seconds()
    content, prompt_version = await _fetch_langfuse_prompt_content(binding)

    if persist:
        await _persist_langfuse_cache(
            model_id,
            binding,
            content,
            prompt_version=prompt_version,
            default_ttl=default_ttl,
            db=db,
        )
    else:
        invalidate_system_prompt_cache(model_id)

    return {
        'content': content,
        'prompt_name': binding.external_name,
        'prompt_version': prompt_version,
    }


async def _persist_langfuse_cache(
    model_id: str,
    binding: ModelSystemPromptBindingModel,
    content: str,
    *,
    prompt_version: str | None,
    default_ttl: int,
    db=None,
) -> None:
    now = int(time.time())
    ttl = _binding_cache_ttl_seconds(binding, default_ttl)
    await ModelSystemPromptBindings.update_cache_fields(
        model_id,
        cached_content=content,
        cached_version=prompt_version,
        cached_at=now,
        cache_ttl_seconds=binding.cache_ttl_seconds,
        db=db,
    )
    set_cached_system_prompt(
        model_id,
        content,
        ttl_seconds=ttl,
        prompt_name=binding.external_name,
        prompt_version=prompt_version,
        cached_at=now,
    )


async def _resolve_langfuse_system_prompt(
    model_info,
    binding: ModelSystemPromptBindingModel,
    metadata: dict | None,
) -> str | None:
    mirror = _get_params_system_mirror(model_info)
    default_ttl = await _get_default_cache_ttl_seconds()
    model_id = model_info.id

    cached = get_cached_system_prompt(model_id)
    if cached and cached.content:
        if metadata is not None:
            metadata.update(
                {
                    'langfuse_prompt_name': cached.prompt_name or binding.external_name,
                    'langfuse_prompt_version': cached.prompt_version or binding.cached_version,
                }
            )
        return cached.content

    if _is_langfuse_cache_warm(binding, default_ttl=default_ttl):
        ttl = _binding_cache_ttl_seconds(binding, default_ttl)
        set_cached_system_prompt(
            model_id,
            binding.cached_content,
            ttl_seconds=ttl,
            prompt_name=binding.external_name,
            prompt_version=binding.cached_version,
            cached_at=binding.cached_at,
        )
        if metadata is not None:
            metadata.update(_langfuse_metadata(binding))
        return binding.cached_content

    try:
        content, prompt_version = await _fetch_langfuse_prompt_content(binding)
        await _persist_langfuse_cache(
            model_id,
            binding,
            content,
            prompt_version=prompt_version,
            default_ttl=default_ttl,
        )
        if metadata is not None:
            metadata.update(_langfuse_metadata(binding, prompt_version=prompt_version))
        return content
    except Exception:
        log.exception(
            'Failed to fetch Langfuse system prompt for model %s (connection=%s, name=%s)',
            model_id,
            binding.connection_id,
            binding.external_name,
        )
        if binding.cached_content:
            if metadata is not None:
                metadata.update(_langfuse_metadata(binding))
            return binding.cached_content
        return mirror


async def _resolve_raw_system_prompt(model_info, metadata: dict | None = None) -> str | None:
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
        return await _resolve_langfuse_system_prompt(model_info, binding, metadata)

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

    raw = await _resolve_raw_system_prompt(model_info, metadata)
    return await resolve_system_prompt(raw, metadata, user)
