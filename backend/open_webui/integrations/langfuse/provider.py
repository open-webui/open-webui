from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.integrations.langfuse.connections import get_connection_by_id, langfuse_basic_auth_header
from open_webui.integrations.system_prompt.factory import SystemPromptProviderBase
from open_webui.models.config import Config
from open_webui.models.model_system_prompt_binding import ModelSystemPromptBindingModel
from open_webui.utils.session_pool import cleanup_response, get_session
from open_webui.utils.system_prompt_cache import (
    acquire_system_prompt_fetch_lock,
    binding_cache_ttl_seconds,
    get_cached_system_prompt,
    is_binding_db_cache_warm,
    is_system_prompt_fetch_backoff_active,
    record_system_prompt_fetch_failure,
    serve_stale_system_prompt_from_binding,
    set_cached_system_prompt,
)

log = logging.getLogger(__name__)

DEFAULT_LANGFUSE_CACHE_TTL_SECONDS = 300


class LangfusePromptError(Exception):
    """Raised when Langfuse prompt fetch or validation fails."""


@dataclass(frozen=True)
class LangfusePromptResult:
    name: str
    content: str
    version: int | str | None
    type: str
    labels: list[str]


class LangfusePromptProvider(SystemPromptProviderBase):
    @staticmethod
    def _attach_metadata(
        binding: ModelSystemPromptBindingModel,
        metadata: dict | None,
        *,
        prompt_version: int | str | None = None,
    ) -> None:
        if metadata is None:
            return
        from open_webui.utils.system_prompt import _langfuse_metadata

        if prompt_version is None:
            metadata.update(_langfuse_metadata(binding))
        else:
            metadata.update(_langfuse_metadata(binding, prompt_version=prompt_version))

    def _serve_memory_cache(
        self,
        model_id: str,
        binding: ModelSystemPromptBindingModel,
        metadata: dict | None,
        *,
        default_ttl: int,
    ) -> str | None:
        effective_ttl = binding_cache_ttl_seconds(binding, default_ttl)
        cached = get_cached_system_prompt(
            model_id,
            effective_ttl_seconds=effective_ttl,
        )
        if not cached or not cached.content:
            return None
        self._attach_metadata(binding, metadata, prompt_version=cached.prompt_version)
        return cached.content

    def _serve_warm_db_cache(
        self,
        model_id: str,
        binding: ModelSystemPromptBindingModel,
        metadata: dict | None,
        *,
        default_ttl: int,
    ) -> str | None:
        if not is_binding_db_cache_warm(binding, default_ttl=default_ttl):
            return None
        ttl = binding_cache_ttl_seconds(binding, default_ttl)
        set_cached_system_prompt(
            model_id,
            binding.cached_content,
            ttl_seconds=ttl,
            prompt_name=binding.external_name,
            prompt_version=binding.cached_version,
            cached_at=binding.cached_at,
        )
        self._attach_metadata(binding, metadata)
        return binding.cached_content

    async def _fetch_under_lock(
        self,
        model_id: str,
        binding: ModelSystemPromptBindingModel,
        *,
        mirror: str | None,
        metadata: dict | None,
        default_ttl: int,
    ) -> str | None:
        cached_content = self._serve_memory_cache(
            model_id,
            binding,
            metadata,
            default_ttl=default_ttl,
        )
        if cached_content is not None:
            return cached_content

        if is_system_prompt_fetch_backoff_active(model_id) and not binding.cached_content:
            return mirror

        try:
            content, prompt_version = await self.fetch_prompt_for_binding(binding)
            from open_webui.utils.system_prompt import _persist_langfuse_cache

            await _persist_langfuse_cache(
                model_id,
                binding,
                content,
                prompt_version=prompt_version,
                default_ttl=default_ttl,
            )
            self._attach_metadata(binding, metadata, prompt_version=prompt_version)
            return content
        except Exception:
            log.exception(
                'Failed to fetch Langfuse system prompt for model %s (connection=%s, name=%s)',
                model_id,
                binding.connection_id,
                binding.external_name,
            )
            record_system_prompt_fetch_failure(model_id)
            if not binding.cached_content:
                return mirror
            serve_stale_system_prompt_from_binding(
                model_id,
                binding,
                default_ttl=default_ttl,
            )
            self._attach_metadata(binding, metadata)
            return binding.cached_content

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

        default_ttl = await _get_default_cache_ttl_seconds()

        cached_content = self._serve_memory_cache(
            model_id,
            binding,
            metadata,
            default_ttl=default_ttl,
        )
        if cached_content is not None:
            return cached_content

        db_content = self._serve_warm_db_cache(
            model_id,
            binding,
            metadata,
            default_ttl=default_ttl,
        )
        if db_content is not None:
            return db_content

        if is_system_prompt_fetch_backoff_active(model_id) and not binding.cached_content:
            return mirror

        fetch_lock = await acquire_system_prompt_fetch_lock(model_id)
        async with fetch_lock:
            return await self._fetch_under_lock(
                model_id,
                binding,
                mirror=mirror,
                metadata=metadata,
                default_ttl=default_ttl,
            )

    async def list_prompts(
        self,
        connection: dict[str, Any],
        *,
        page: int = 1,
        limit: int = 50,
        name: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        base_url = (connection.get('url') or '').rstrip('/')
        public_key = (connection.get('public_key') or '').strip()
        secret_key = (connection.get('secret_key') or '').strip()
        if not base_url:
            raise LangfusePromptError('Langfuse URL is required')
        if not public_key or not secret_key:
            raise LangfusePromptError('Langfuse public and secret keys are required')

        params: dict[str, str | int] = {'page': page, 'limit': limit}
        if name:
            params['name'] = name
        if label:
            params['label'] = label

        headers = langfuse_basic_auth_header(public_key, secret_key)
        session = await get_session()
        response = await session.get(
            f'{base_url}/api/public/v2/prompts',
            headers=headers,
            params=params,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        try:
            if not response.ok:
                raise LangfusePromptError(f'Langfuse list prompts failed (HTTP {response.status})')
            return await response.json()
        finally:
            await cleanup_response(response)

    async def get_prompt(
        self,
        connection: dict[str, Any],
        name: str,
        *,
        label: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        result = await self._fetch_prompt(connection, name, label=label, version=version)
        return {
            'name': result.name,
            'content': result.content,
            'version': result.version,
            'type': result.type,
            'labels': result.labels,
        }

    async def fetch_prompt(
        self,
        connection: dict[str, Any],
        name: str,
        *,
        label: str | None = None,
        version: str | None = None,
    ) -> LangfusePromptResult:
        return await self._fetch_prompt(connection, name, label=label, version=version)

    async def _fetch_prompt(
        self,
        connection: dict[str, Any],
        name: str,
        *,
        label: str | None = None,
        version: str | None = None,
    ) -> LangfusePromptResult:
        base_url = (connection.get('url') or '').rstrip('/')
        public_key = (connection.get('public_key') or '').strip()
        secret_key = (connection.get('secret_key') or '').strip()
        if not base_url:
            raise LangfusePromptError('Langfuse URL is required')
        if not public_key or not secret_key:
            raise LangfusePromptError('Langfuse public and secret keys are required')
        if not name:
            raise LangfusePromptError('Langfuse prompt name is required')

        params: dict[str, str] = {}
        if version:
            params['version'] = str(version)
        elif label:
            params['label'] = label

        encoded_name = quote(name, safe='')
        headers = langfuse_basic_auth_header(public_key, secret_key)
        session = await get_session()
        response = await session.get(
            f'{base_url}/api/public/v2/prompts/{encoded_name}',
            headers=headers,
            params=params or None,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        try:
            if not response.ok:
                raise LangfusePromptError(f'Langfuse get prompt failed (HTTP {response.status})')
            data = await response.json()
        finally:
            await cleanup_response(response)

        return self._parse_prompt_payload(data, expected_name=name)

    async def fetch_prompt_for_binding(
        self,
        binding: ModelSystemPromptBindingModel,
    ) -> tuple[str, str | None]:
        if not binding.connection_id or not binding.external_name:
            raise LangfusePromptError('Langfuse binding is missing connection_id or external_name')

        connection = await get_connection_by_id(binding.connection_id)
        if not connection or not connection.get('enabled', True):
            raise LangfusePromptError('Langfuse connection is missing or disabled')

        result = await self.fetch_prompt(
            connection,
            binding.external_name,
            label=binding.external_label,
            version=binding.external_version,
        )
        version = str(result.version) if result.version is not None else None
        return result.content, version

    @staticmethod
    def _parse_prompt_payload(data: dict[str, Any], *, expected_name: str) -> LangfusePromptResult:
        prompt_type = data.get('type') or 'text'
        if prompt_type == 'chat':
            raise LangfusePromptError(
                'Langfuse chat prompts are not supported for model system prompts; use a text prompt.'
            )

        content = data.get('prompt')
        if not isinstance(content, str):
            raise LangfusePromptError('Unexpected Langfuse text prompt payload')
        if not content:
            raise LangfusePromptError('Langfuse prompt content must not be empty')

        return LangfusePromptResult(
            name=data.get('name') or expected_name,
            content=content,
            version=data.get('version'),
            type=prompt_type,
            labels=list(data.get('labels') or []),
        )

    # future: emit_trace


async def _get_default_cache_ttl_seconds() -> int:
    ttl = await Config.get('langfuse.prompt_cache_ttl')
    return ttl if ttl is not None else DEFAULT_LANGFUSE_CACHE_TTL_SECONDS
