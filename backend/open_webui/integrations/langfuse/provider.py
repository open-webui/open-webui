from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.integrations.langfuse.connections import langfuse_basic_auth_header
from open_webui.integrations.system_prompt.factory import SystemPromptProviderBase
from open_webui.utils.session_pool import cleanup_response, get_session

log = logging.getLogger(__name__)


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
                detail = await response.text()
                raise LangfusePromptError(
                    f'Langfuse list prompts failed ({response.status}): {detail}'
                )
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
                detail = await response.text()
                raise LangfusePromptError(
                    f'Langfuse get prompt failed ({response.status}): {detail}'
                )
            data = await response.json()
        finally:
            await cleanup_response(response)

        return self._parse_prompt_payload(data, expected_name=name)

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

        return LangfusePromptResult(
            name=data.get('name') or expected_name,
            content=content,
            version=data.get('version'),
            type=prompt_type,
            labels=list(data.get('labels') or []),
        )

    # future: emit_trace
