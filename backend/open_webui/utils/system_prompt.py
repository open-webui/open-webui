import logging
import time

from open_webui.integrations.system_prompt.factory import SystemPromptProvider
from open_webui.models.config import Config
from open_webui.models.model_system_prompt_binding import (
    ModelSystemPromptBindingModel,
    ModelSystemPromptBindings,
)
from open_webui.utils.system_prompt_cache import (
    binding_cache_ttl_seconds,
    get_cached_system_prompt_async,
    invalidate_system_prompt_cache,
    is_cache_age_warm,
    is_newer_cache_write,
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
    from open_webui.integrations.langfuse.provider import LangfusePromptProvider

    provider = SystemPromptProvider.get_provider('langfuse')
    if not isinstance(provider, LangfusePromptProvider):
        raise RuntimeError('Langfuse provider misconfigured')
    return await provider.fetch_prompt_for_binding(binding)


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
    ttl = binding_cache_ttl_seconds(binding, default_ttl)

    current = await ModelSystemPromptBindings.get_by_model_id(model_id, db=db)
    if current and not is_newer_cache_write(
        current.cached_at,
        current.cached_version,
        now,
        prompt_version,
    ):
        log.debug(
            'Skipping Langfuse cache persist for model %s: existing cache is newer',
            model_id,
        )
        set_cached_system_prompt(
            model_id,
            current.cached_content or content,
            ttl_seconds=ttl,
            prompt_name=binding.external_name,
            prompt_version=current.cached_version or prompt_version,
            cached_at=current.cached_at,
        )
        return

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


def _apply_lru_metadata(cached, metadata: dict | None) -> None:
    if metadata is None:
        return
    if cached.prompt_name is not None:
        metadata['langfuse_prompt_name'] = cached.prompt_name
    if cached.prompt_version is not None:
        metadata['langfuse_prompt_version'] = cached.prompt_version


async def _resolve_raw_system_prompt(model_info, metadata: dict | None = None) -> str | None:
    mirror = _get_params_system_mirror(model_info)
    model_id = model_info.id

    cached = await get_cached_system_prompt_async(model_id)
    if cached is not None:
        try:
            binding = await ModelSystemPromptBindings.get_by_model_id(model_id)
        except Exception:
            log.exception('Failed to load system prompt binding for model %s', model_id)
            _apply_lru_metadata(cached, metadata)
            return cached.content

        if binding:
            if binding.source == 'local':
                from open_webui.integrations.system_prompt.local import (
                    DEFAULT_LOCAL_CACHE_TTL_SECONDS,
                )

                default_ttl = DEFAULT_LOCAL_CACHE_TTL_SECONDS
            else:
                default_ttl = await _get_default_cache_ttl_seconds()
            effective_ttl = binding_cache_ttl_seconds(binding, default_ttl)
            if is_cache_age_warm(cached.cached_at, effective_ttl):
                _apply_lru_metadata(cached, metadata)
                return cached.content
        else:
            _apply_lru_metadata(cached, metadata)
            return cached.content

        invalidate_system_prompt_cache(model_id)

    try:
        binding = await ModelSystemPromptBindings.get_by_model_id(model_id)
    except Exception:
        log.exception('Failed to load system prompt binding for model %s', model_id)
        return mirror

    if not binding:
        return mirror

    try:
        provider = SystemPromptProvider.get_provider(binding.source)
    except ValueError:
        log.warning(
            'Unknown system prompt source %r for model %s; falling back to params.system mirror',
            binding.source,
            model_id,
        )
        return mirror

    return await provider.resolve_content(
        binding,
        mirror=mirror,
        metadata=metadata,
        model_id=model_id,
    )


async def resolve_model_system_prompt(
    model_info,  # ModelModel | None
    metadata: dict | None,
    user,
    *,
    bypass: bool = False,
) -> str:
    """Resolve the raw model system prompt from binding/source without templating."""
    if bypass or model_info is None:
        return ''

    raw = await _resolve_raw_system_prompt(model_info, metadata)
    return raw or ''
