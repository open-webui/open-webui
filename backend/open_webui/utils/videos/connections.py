"""Video connections: the configured backends that built-in video generation runs on.

A connection is one OpenAI compatible server with a video API (``/videos``), such as LiteLLM,
OpenAI or OpenRouter, or a ComfyUI server running the admin's video workflow, with the video models it
exposes. Users pick a model by its reference,
``{connection_id}:{model_id}``, and only see models their access grants allow.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from aiocache import cached
from fastapi import HTTPException, Request
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, MODELS_CACHE_TTL
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.users import UserModel
from open_webui.utils.access_control import has_connection_access
from open_webui.utils.headers import get_headers_and_cookies
from open_webui.utils.images.connections import (
    IMAGE_CONNECTION_AUTH_TYPES,
    _json_object,
    _size,
    _workflow,
    _workflow_nodes,
    get_image_model_ref,
    get_openai_connection_models,
    get_requested_model,
)
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

VIDEO_CONNECTIONS_CONFIG_KEY = 'videos.connections'
VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY = 'video_generation.default_model'

VIDEO_CONNECTION_TYPES = ('openai', 'comfyui')
VIDEO_CONNECTION_AUTH_TYPES = IMAGE_CONNECTION_AUTH_TYPES

# Like chat model connections: '' is the OpenAI video API (OpenAI, LiteLLM); OpenRouter has its own.
VIDEO_CONNECTION_PROVIDERS = ('', 'openrouter')


def get_video_connection_provider(connection: dict) -> str:
    """The API a connection speaks: the admin's choice, else OpenRouter when the URL is OpenRouter's."""
    provider = (connection.get('config') or {}).get('provider') or ''
    if not provider and 'openrouter.ai' in (connection.get('url') or ''):
        return 'openrouter'
    return provider


def normalize_video_connection(connection: dict[str, Any]) -> dict[str, Any]:
    """Validate a video connection and fill in defaults. Raises ValueError on invalid input."""
    connection_type = str(connection.get('type') or 'openai')
    if connection_type not in VIDEO_CONNECTION_TYPES:
        raise ValueError(f'Unsupported video connection type: {connection_type}')

    connection_id = str(connection.get('id') or uuid.uuid4())
    if ':' in connection_id:
        raise ValueError('Video connection IDs cannot contain ":"')

    config = connection.get('config') or {}

    model_ids = []
    for model_id in config.get('model_ids') or []:
        model_id = str(model_id).strip()
        if model_id and model_id not in model_ids:
            model_ids.append(model_id)

    auth_type = str(config.get('auth_type') or 'bearer')
    if auth_type not in VIDEO_CONNECTION_AUTH_TYPES:
        raise ValueError(f'Unsupported auth type: {auth_type}')
    if connection_type != 'openai' and auth_type not in ('none', 'bearer'):
        raise ValueError(f'{connection_type} connections support no auth or a key')

    provider = str(config.get('provider') or '') if connection_type == 'openai' else ''
    if provider not in VIDEO_CONNECTION_PROVIDERS:
        raise ValueError(f'Unsupported video provider: {provider}')

    seconds = config.get('seconds')
    if seconds not in (None, ''):
        seconds = int(seconds)
        if seconds <= 0:
            raise ValueError('Video length must be a positive number of seconds (e.g. 8)')
    else:
        seconds = None

    fps = config.get('fps')
    if fps not in (None, ''):
        fps = float(fps)
        if fps <= 0:
            raise ValueError('Frame rate must be a positive number of frames per second (e.g. 24)')
    else:
        fps = None

    return {
        'id': connection_id,
        'name': str(connection.get('name') or '').strip() or connection_type,
        'type': connection_type,
        'url': str(connection.get('url') or '').strip().rstrip('/'),
        'key': str(connection.get('key') or ''),
        'config': {
            'enable': bool(config.get('enable', True)),
            'model_ids': model_ids,
            'access_grants': list(config.get('access_grants') or []),
            'provider': provider,
            'auth_type': auth_type,
            'headers': _json_object(config.get('headers'), 'headers'),
            'size': _size(config.get('size')),
            'seconds': seconds,
            'api_version': str(config.get('api_version') or ''),
            'params': _json_object(config.get('params'), 'additional parameters'),
            'workflow': _workflow(config.get('workflow'), 'ComfyUI workflow'),
            'nodes': _workflow_nodes(config.get('nodes')),
            'fps': fps,
        },
    }


async def get_video_connection_models(request: Request, connection: dict, user: UserModel | None = None) -> list[dict]:
    """The models a connection serves, with video models marked (``video``). OpenRouter lists its video
    models on their own at ``/videos/models``; other servers list everything at ``/models``, and LiteLLM
    marks which ones make video. ComfyUI offers the models its workflow's model node can load."""
    if connection.get('type') == 'comfyui':
        from open_webui.routers.images import get_comfyui_connection_models

        return [{**model, 'video': True} for model in await get_comfyui_connection_models(connection)]

    if get_video_connection_provider(connection) != 'openrouter':
        return await get_openai_connection_models(request, connection, user)

    from open_webui.routers.images import raise_for_provider_status

    headers, cookies = await get_headers_and_cookies(
        request, connection['url'], connection.get('key'), connection.get('config') or {}, user=user
    )
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/videos/models', headers=headers, cookies=cookies, ssl=AIOHTTP_CLIENT_SESSION_SSL
    ) as r:
        await raise_for_provider_status(r)
        res = await r.json(content_type=None)

    entries = res.get('data') if isinstance(res, dict) else res
    return [
        {'id': entry['id'], 'name': entry.get('name') or entry['id'], 'video': True}
        for entry in entries or []
        if isinstance(entry, dict) and entry.get('id')
    ]


@cached(
    ttl=MODELS_CACHE_TTL,
    key_builder=lambda _func, request, connection, user=None: (
        f'video_connection_models_{connection["id"]}_{user.id}'
        if user
        else f'video_connection_models_{connection["id"]}'
    ),
)
async def get_synced_video_models(request: Request, connection: dict, user: UserModel | None = None) -> list[dict]:
    """The video models a connection with no model IDs offers, listed live so new ones appear on their own.
    Servers that do not label video models (plain OpenAI) offer their default model."""
    try:
        models = await get_video_connection_models(request, connection, user)
    except Exception as e:
        log.warning('Could not list video models from %s: %s', connection.get('url'), e)
        return []

    if not any('video' in model for model in models):
        return [{'id': ''}]
    return [model for model in models if model['video']]


async def get_video_models(request: Request, user: UserModel, *, bypass_access: bool = False) -> list[dict]:
    """Video models the user may use, across enabled connections. Each carries its connection for internal use.

    A connection without model IDs offers every video model the server labels (LiteLLM), else its default
    model, or for ComfyUI the model its workflow sets.
    """
    connections = await Config.get(VIDEO_CONNECTIONS_CONFIG_KEY) or []
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}

    models = []
    for connection in connections:
        config = connection.get('config') or {}
        if not config.get('enable', True):
            continue
        if not bypass_access and not await has_connection_access(user, connection, user_group_ids):
            continue

        if config.get('model_ids'):
            entries = [{'id': model_id} for model_id in config['model_ids']]
        elif connection.get('type') == 'comfyui':
            entries = [{'id': ''}]
        else:
            entries = await get_synced_video_models(request, connection, user)

        for entry in entries:
            model_id = entry['id']
            models.append(
                {
                    'id': get_image_model_ref(connection['id'], model_id),
                    'name': model_id or connection.get('name') or connection['id'],
                    'model': model_id,
                    'connection_id': connection['id'],
                    'connection_name': connection.get('name') or connection['id'],
                    'connection': connection,
                }
            )
    return models


def get_requested_video_model(metadata: dict | None) -> str | None:
    return get_requested_model(metadata, 'video_generation', 'videoModelId')


async def resolve_video_model(
    request: Request,
    user: UserModel,
    model: str | None = None,
    *,
    strict: bool = False,
) -> tuple[dict, str]:
    """Pick the connection and model to run a request on.

    Order: the requested model (a reference or a bare model id), then the admin's default, then the
    first model the user can use. A requested model the user cannot use falls back to the default
    unless ``strict`` is set, as on the direct API route.
    """
    models = await get_video_models(request, user)

    def find(value: str | None) -> dict | None:
        if not value:
            return None
        return next((m for m in models if m['id'] == value), None) or next(
            (m for m in models if m['model'] == value), None
        )

    if model:
        requested = find(model)
        if requested:
            return requested['connection'], requested['model']
        if strict:
            raise HTTPException(status_code=400, detail=f'Video model "{model}" was not found')
        log.debug('Video model %s is not available to %s; using the default', model, user.id)

    default = find(await Config.get(VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY))
    if default:
        return default['connection'], default['model']

    if models:
        return models[0]['connection'], models[0]['model']

    raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('No video model is available'))
