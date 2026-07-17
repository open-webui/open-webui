from __future__ import annotations

from typing import Any

from open_webui.integrations.system_prompt.factory import SystemPromptProviderBase
from open_webui.models.model_system_prompt_binding import ModelSystemPromptBindingModel
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions


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
        if binding.active_version_id:
            version = await ModelSystemPromptVersions.get_version_by_id(binding.active_version_id)
            if version and version.content:
                return version.content
        return mirror

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
