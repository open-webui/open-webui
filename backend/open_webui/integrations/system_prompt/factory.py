from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from open_webui.models.model_system_prompt_binding import ModelSystemPromptBindingModel


class SystemPromptProviderBase(ABC):
    """Base interface for system prompt source backends."""

    @abstractmethod
    async def resolve_content(
        self,
        binding: ModelSystemPromptBindingModel,
        *,
        mirror: str | None = None,
        metadata: dict | None = None,
        model_id: str | None = None,
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def list_prompts(
        self,
        connection: dict[str, Any],
        *,
        page: int = 1,
        limit: int = 50,
        name: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_prompt(
        self,
        connection: dict[str, Any],
        name: str,
        *,
        label: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class SystemPromptProvider:
    @staticmethod
    def get_provider(source: str) -> SystemPromptProviderBase:
        match source:
            case 'local':
                from open_webui.integrations.system_prompt.local import LocalSystemPromptProvider

                return LocalSystemPromptProvider()
            case 'langfuse':
                from open_webui.integrations.langfuse.provider import LangfusePromptProvider

                return LangfusePromptProvider()
            case _:
                raise ValueError(f'Unsupported system prompt source: {source}')
