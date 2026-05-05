"""
title: Vertex AI (Gemini + Claude)
author: pioneer-chat
author_url: https://github.com/swept-ai/open-webui
version: 0.1.0
license: MIT
required_open_webui_version: 0.5.0
requirements: google-genai>=1.0.0, anthropic[vertex]>=0.40.0
"""

import json
import logging
import os
from typing import AsyncGenerator

from pydantic import BaseModel, Field


log = logging.getLogger(__name__)


class Pipe:
    class Valves(BaseModel):
        VERTEX_PROJECT_ID: str = Field(
            default_factory=lambda: os.getenv('VERTEX_PROJECT_ID', ''),
            description='GCP project that hosts Vertex AI (e.g. "pioneer-insurance").',
        )
        VERTEX_LOCATION: str = Field(
            default_factory=lambda: os.getenv('VERTEX_LOCATION', 'us-central1'),
            description='Vertex region. Use "global" for broadest Gemini availability.',
        )
        GEMINI_MODELS: str = Field(
            default='gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-lite',
            description='Comma-separated Gemini model ids visible in the picker.',
        )
        CLAUDE_MODELS: str = Field(
            default='claude-opus-4@20250514,claude-sonnet-4-5@20251001,claude-haiku-4-5@20251001',
            description=(
                'Comma-separated Claude-on-Vertex model ids (publisher@version). '
                'Each must be enabled in GCP > Vertex AI > Model Garden.'
            ),
        )
        CLAUDE_LOCATION: str = Field(
            default_factory=lambda: os.getenv('VERTEX_CLAUDE_LOCATION', 'us-east5'),
            description=(
                'Region for Claude on Vertex (separate from Gemini location: '
                'Anthropic models are only available in specific regions like us-east5, europe-west1).'
            ),
        )

    def __init__(self):
        self.type = 'manifold'
        self.id = 'vertex'
        self.name = 'Vertex / '
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        models: list[dict] = []
        for m in _split_csv(self.valves.GEMINI_MODELS):
            models.append({'id': f'gemini::{m}', 'name': f'Gemini {m}'})
        for m in _split_csv(self.valves.CLAUDE_MODELS):
            display = m.split('@', 1)[0]
            models.append({'id': f'claude::{m}', 'name': f'Claude {display}'})
        return models

    async def pipe(self, body: dict, __user__: dict | None = None):
        sub_id = body['model'].split('.', 1)[-1]
        try:
            provider, model = sub_id.split('::', 1)
        except ValueError as exc:
            raise ValueError(f"unexpected model id '{sub_id}' (expected 'provider::model')") from exc

        stream = bool(body.get('stream', False))
        messages = body.get('messages', []) or []
        temperature = body.get('temperature')
        max_tokens = body.get('max_tokens')

        if provider == 'gemini':
            return _gemini(
                model=model,
                messages=messages,
                project=self.valves.VERTEX_PROJECT_ID,
                location=self.valves.VERTEX_LOCATION,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == 'claude':
            return _claude(
                model=model,
                messages=messages,
                project=self.valves.VERTEX_PROJECT_ID,
                region=self.valves.CLAUDE_LOCATION,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise ValueError(f"unknown provider in '{sub_id}': {provider}")


def _split_csv(value: str) -> list[str]:
    return [s.strip() for s in (value or '').split(',') if s.strip()]


def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system_parts: list[str] = []
    rest: list[dict] = []
    for m in messages:
        if m.get('role') == 'system':
            content = m.get('content')
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        system_parts.append(c.get('text', ''))
        else:
            rest.append(m)
    system = '\n\n'.join(p for p in system_parts if p) or None
    return system, rest


def _gemini(
    *,
    model: str,
    messages: list[dict],
    project: str,
    location: str,
    stream: bool,
    temperature: float | None,
    max_tokens: int | None,
):
    from google import genai
    from google.genai import types as genai_types

    if not project:
        raise RuntimeError('VERTEX_PROJECT_ID is not set (env var or Function valve).')

    client = genai.Client(vertexai=True, project=project, location=location)

    system, chat_messages = _split_system(messages)
    contents = [_to_gemini_content(m) for m in chat_messages]

    config = genai_types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    if stream:
        async def gen() -> AsyncGenerator[str, None]:
            stream_iter = await client.aio.models.generate_content_stream(
                model=model, contents=contents, config=config,
            )
            async for chunk in stream_iter:
                text = getattr(chunk, 'text', None)
                if text:
                    yield text
        return gen()

    async def once():
        resp = await client.aio.models.generate_content(
            model=model, contents=contents, config=config,
        )
        return resp.text or ''

    return once()


def _to_gemini_content(message: dict) -> dict:
    role = 'user' if message.get('role') == 'user' else 'model'
    raw = message.get('content')
    parts: list[dict] = []
    if isinstance(raw, str):
        parts.append({'text': raw})
    elif isinstance(raw, list):
        for c in raw:
            if not isinstance(c, dict):
                continue
            ctype = c.get('type')
            if ctype == 'text':
                parts.append({'text': c.get('text', '')})
            elif ctype == 'image_url':
                url = (c.get('image_url') or {}).get('url', '')
                if url.startswith('data:'):
                    header, _, b64 = url.partition(',')
                    mime = header.split(';')[0].removeprefix('data:') or 'image/png'
                    parts.append({'inline_data': {'mime_type': mime, 'data': b64}})
                elif url:
                    parts.append({'file_data': {'file_uri': url, 'mime_type': 'image/*'}})
    return {'role': role, 'parts': parts or [{'text': ''}]}


def _claude(
    *,
    model: str,
    messages: list[dict],
    project: str,
    region: str,
    stream: bool,
    temperature: float | None,
    max_tokens: int | None,
):
    from anthropic import AsyncAnthropicVertex

    if not project:
        raise RuntimeError('VERTEX_PROJECT_ID is not set (env var or Function valve).')

    client = AsyncAnthropicVertex(project_id=project, region=region)
    system, chat_messages = _split_system(messages)
    payload_messages = [_to_anthropic_message(m) for m in chat_messages]

    kwargs: dict = {
        'model': model,
        'messages': payload_messages,
        'max_tokens': max_tokens or 4096,
    }
    if system is not None:
        kwargs['system'] = system
    if temperature is not None:
        kwargs['temperature'] = temperature

    if stream:
        async def gen() -> AsyncGenerator[str, None]:
            async with client.messages.stream(**kwargs) as s:
                async for text in s.text_stream:
                    if text:
                        yield text
        return gen()

    async def once():
        resp = await client.messages.create(**kwargs)
        return ''.join(b.text for b in resp.content if getattr(b, 'type', None) == 'text')

    return once()


def _to_anthropic_message(message: dict) -> dict:
    role = 'user' if message.get('role') == 'user' else 'assistant'
    raw = message.get('content')
    if isinstance(raw, str):
        return {'role': role, 'content': raw}

    blocks: list[dict] = []
    if isinstance(raw, list):
        for c in raw:
            if not isinstance(c, dict):
                continue
            ctype = c.get('type')
            if ctype == 'text':
                blocks.append({'type': 'text', 'text': c.get('text', '')})
            elif ctype == 'image_url':
                url = (c.get('image_url') or {}).get('url', '')
                if url.startswith('data:'):
                    header, _, b64 = url.partition(',')
                    mime = header.split(';')[0].removeprefix('data:') or 'image/png'
                    blocks.append({
                        'type': 'image',
                        'source': {'type': 'base64', 'media_type': mime, 'data': b64},
                    })
                elif url:
                    blocks.append({
                        'type': 'image',
                        'source': {'type': 'url', 'url': url},
                    })
    return {'role': role, 'content': blocks or [{'type': 'text', 'text': ''}]}
