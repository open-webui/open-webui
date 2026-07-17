from __future__ import annotations

from typing import Any

from open_webui.integrations.system_prompt.factory import SystemPromptProviderBase
from open_webui.models.model_system_prompt_binding import ModelSystemPromptBindingModel
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions
from open_webui.utils.system_prompt_cache import (
    binding_cache_ttl_seconds,
    set_cached_system_prompt,
)

DEFAULT_LOCAL_CACHE_TTL_SECONDS = 3600


class LocalSystemPromptProvider(SystemPromptProviderBase):
    """Local version-backed system prompt provider."""

    async def resolve_content(
        self,
        binding: ModelSystemPromptBindingModel,
        *,
        mirror: str | None = None,
        metadata: dict | None = None,
        model_id: str | None = None,
    ) -> str | None:
        if model_id is None:
            model_id = binding.model_id

        content = mirror
        prompt_version: str | None = None
        version = None

        if binding.active_version_id:
            version = await ModelSystemPromptVersions.get_version_by_id(binding.active_version_id)
            if version is not None:
                content = version.content
                prompt_version = binding.active_version_id

        if version is not None:
            ttl = binding_cache_ttl_seconds(binding, DEFAULT_LOCAL_CACHE_TTL_SECONDS)
            if ttl > 0 and model_id:
                set_cached_system_prompt(
                    model_id,
                    content if content is not None else '',
                    ttl_seconds=ttl,
                    prompt_version=prompt_version,
                )

        return content

    async def list_prompts(
        self,
        connection: dict[str, Any],
        *,
        page: int = 1,
        limit: int = 50,
        name: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError('Local system prompt provider does not support list_prompts')

    async def get_prompt(
        self,
        connection: dict[str, Any],
        name: str,
        *,
        label: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError('Local system prompt provider does not support get_prompt')
