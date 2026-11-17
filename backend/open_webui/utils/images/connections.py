"""Image connections: the configured backends that built-in image generation and editing run on.

A connection is one backend (an OpenAI-compatible endpoint such as LiteLLM, Gemini, ComfyUI or
AUTOMATIC1111) with the image models it exposes. Users pick a model by its reference,
``{connection_id}:{model_id}``, and only see models their access grants allow.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from aiocache import cached
from fastapi import HTTPException, Request
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, MODELS_CACHE_TTL
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.users import UserModel
from open_webui.utils.access_control import has_connection_access
from open_webui.utils.headers import get_headers_and_cookies
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

IMAGE_CONNECTIONS_CONFIG_KEY = 'images.connections'
IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY = 'image_generation.default_model'
IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY = 'images.edit.default_model'

IMAGE_CONNECTION_TYPES = ('openai', 'gemini', 'comfyui', 'automatic1111')

# The auth types chat model connections offer; only OpenAI compatible image connections use more than a key.
IMAGE_CONNECTION_AUTH_TYPES = ('none', 'bearer', 'session', 'system_oauth', 'microsoft_entra_id')

DEFAULT_OPENAI_IMAGE_MODEL = 'gpt-image-2'
DEFAULT_GEMINI_IMAGE_MODEL = 'imagen-3.0-generate-002'

ImageCapability = Literal['image_generation', 'image_edit']

IMAGE_CAPABILITIES: tuple[ImageCapability, ...] = ('image_generation', 'image_edit')

PUBLIC_ACCESS_GRANTS = [{'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}]


def get_image_model_ref(connection_id: str, model_id: str) -> str:
    return f'{connection_id}:{model_id}'


def _json_object(value: Any, label: str) -> dict:
    if value in (None, ''):
        return {}
    if isinstance(value, str):
        try:
            value = JSONCodec.loads(value)
        except JSONCodec.JSONDecodeError:
            raise ValueError(f'Invalid JSON for {label}')
    if not isinstance(value, dict):
        raise ValueError(f'Invalid JSON for {label}')
    return value


def _workflow(value: Any, label: str) -> str:
    if value in (None, ''):
        return ''
    if isinstance(value, dict):
        return JSONCodec.dumps(value)
    _json_object(value, label)
    return str(value)


def _size(value: Any) -> str:
    size = str(value or '').strip()
    if size and size != 'auto':
        width, _, height = size.partition('x')
        if not (width.isdigit() and height.isdigit()):
            raise ValueError(f'Invalid image size: {size} (e.g. 512x512)')
    return size


def _workflow_nodes(nodes: Any) -> list[dict]:
    normalized = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        node_ids = node.get('node_ids') or []
        if isinstance(node_ids, str):
            node_ids = [node_id.strip() for node_id in node_ids.split(',') if node_id.strip()]
        normalized.append(
            {
                'type': str(node.get('type') or ''),
                'key': str(node.get('key') or ''),
                'node_ids': [str(node_id) for node_id in node_ids],
            }
        )
    return normalized


def normalize_image_connection(connection: dict[str, Any]) -> dict[str, Any]:
    """Validate an image connection and fill in defaults. Raises ValueError on invalid input."""
    connection_type = str(connection.get('type') or 'openai')
    if connection_type not in IMAGE_CONNECTION_TYPES:
        raise ValueError(f'Unsupported image connection type: {connection_type}')

    connection_id = str(connection.get('id') or uuid.uuid4())
    if ':' in connection_id:
        raise ValueError('Image connection IDs cannot contain ":"')

    config = connection.get('config') or {}

    model_ids = []
    for model_id in config.get('model_ids') or []:
        model_id = str(model_id).strip()
        if model_id and model_id not in model_ids:
            model_ids.append(model_id)

    auth_type = str(config.get('auth_type') or 'bearer')
    if auth_type not in IMAGE_CONNECTION_AUTH_TYPES:
        raise ValueError(f'Unsupported auth type: {auth_type}')
    if connection_type != 'openai' and auth_type not in ('none', 'bearer'):
        raise ValueError(f'{connection_type} connections support no auth or a key')

    steps = config.get('steps')
    if steps not in (None, ''):
        steps = int(steps)
        if steps < 0:
            raise ValueError('Steps must be a positive number (e.g. 50)')
    else:
        steps = None

    return {
        'id': connection_id,
        'name': str(connection.get('name') or '').strip() or connection_type,
        'type': connection_type,
        'url': str(connection.get('url') or '').strip().rstrip('/'),
        'key': str(connection.get('key') or ''),
        'config': {
            'enable': bool(config.get('enable', True)),
            'capabilities': {
                capability: bool((config.get('capabilities') or {}).get(capability, True))
                for capability in IMAGE_CAPABILITIES
            },
            'model_ids': model_ids,
            'access_grants': list(config.get('access_grants') or []),
            'auth_type': auth_type,
            'headers': _json_object(config.get('headers'), 'headers'),
            'size': _size(config.get('size')),
            'edit_size': _size(config.get('edit_size')),
            'steps': steps,
            'api_version': str(config.get('api_version') or ''),
            'params': _json_object(config.get('params'), 'additional parameters'),
            'endpoint_method': str(config.get('endpoint_method') or ''),
            'workflow': _workflow(config.get('workflow'), 'ComfyUI workflow'),
            'nodes': _workflow_nodes(config.get('nodes')),
            'edit_workflow': _workflow(config.get('edit_workflow'), 'ComfyUI edit workflow'),
            'edit_nodes': _workflow_nodes(config.get('edit_nodes')),
        },
    }


def get_image_connection_capabilities(connection: dict) -> dict[str, bool]:
    """What a connection's models can do: what its type supports (ComfyUI needs the matching
    workflow, AUTOMATIC1111 cannot edit), narrowed by the capabilities the admin turned on."""
    config = connection.get('config') or {}
    if connection.get('type') == 'automatic1111':
        supported = {'image_generation': True, 'image_edit': False}
    elif connection.get('type') == 'comfyui':
        supported = {'image_generation': bool(config.get('workflow')), 'image_edit': bool(config.get('edit_workflow'))}
    else:
        supported = {'image_generation': True, 'image_edit': True}

    enabled = config.get('capabilities') or {}
    return {capability: supported[capability] and bool(enabled.get(capability, True)) for capability in supported}


async def get_openai_connection_models(request: Request, connection: dict, user: UserModel | None = None) -> list[dict]:
    """The models an OpenAI compatible connection serves. LiteLLM also reports each one's mode and endpoints,
    which mark its image models (``image``) and what they can do, and its video models (``video``)."""
    from open_webui.routers.images import raise_for_provider_status

    headers, cookies = await get_headers_and_cookies(
        request, connection['url'], connection.get('key'), connection.get('config') or {}, user=user
    )
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/models', headers=headers, cookies=cookies, ssl=AIOHTTP_CLIENT_SESSION_SSL
    ) as r:
        await raise_for_provider_status(r)
        res = await r.json(content_type=None)

    models = [
        {'id': model['id'], 'name': model['id']}
        for model in (res.get('data') or [])
        if isinstance(model, dict) and model.get('id')
    ]

    try:
        async with session.get(
            url=f'{connection["url"]}/model/info', headers=headers, cookies=cookies, ssl=AIOHTTP_CLIENT_SESSION_SSL
        ) as r:
            info = await r.json(content_type=None) if r.ok else {}
    except Exception as e:
        log.debug('No model info at %s: %s', connection['url'], e)
        return models

    model_infos = {
        entry.get('model_name'): entry.get('model_info') or {}
        for entry in (info.get('data') or [])
        if isinstance(entry, dict)
    }
    if not any(model_info.get('mode') for model_info in model_infos.values()):
        return models

    for model in models:
        model_info = model_infos.get(model['id']) or {}
        endpoints = [str(endpoint) for endpoint in model_info.get('supported_endpoints') or []]
        if endpoints:
            capabilities = {
                'image_generation': any(endpoint.endswith('/images/generations') for endpoint in endpoints),
                'image_edit': any(endpoint.endswith('/images/edits') for endpoint in endpoints),
            }
            model['video'] = any(endpoint.endswith('/videos') for endpoint in endpoints)
        else:
            capabilities = {capability: model_info.get('mode') == capability for capability in IMAGE_CAPABILITIES}
            model['video'] = model_info.get('mode') == 'video_generation'
        model['image'] = any(capabilities.values())
        if model['image']:
            model.update(capabilities)
    return models


@cached(
    ttl=MODELS_CACHE_TTL,
    key_builder=lambda _func, request, connection, user=None: (
        f'image_connection_models_{connection["id"]}_{user.id}'
        if user
        else f'image_connection_models_{connection["id"]}'
    ),
)
async def get_synced_image_models(request: Request, connection: dict, user: UserModel | None = None) -> list[dict]:
    """The image models an OpenAI compatible connection with no model IDs offers, listed live so new ones
    appear on their own. Servers that do not label image models (plain OpenAI, Azure) offer the default model."""
    try:
        models = await get_openai_connection_models(request, connection, user)
    except Exception as e:
        log.warning('Could not list image models from %s: %s', connection.get('url'), e)
        return []

    if not any('image' in model for model in models):
        return [{'id': ''}]
    return [model for model in models if model['image']]


async def get_image_models(request: Request, user: UserModel, *, bypass_access: bool = False) -> list[dict]:
    """Image models the user may use, across enabled connections. Each carries its connection for internal use.

    A connection without model IDs offers its default: every image model an OpenAI compatible server
    labels (LiteLLM), else the engine's default model, the model a ComfyUI workflow sets, or the
    checkpoint AUTOMATIC1111 has loaded.
    """
    connections = await Config.get(IMAGE_CONNECTIONS_CONFIG_KEY) or []
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}

    models = []
    for connection in connections:
        config = connection.get('config') or {}
        if not config.get('enable', True):
            continue
        if not bypass_access and not await has_connection_access(user, connection, user_group_ids):
            continue
        capabilities = get_image_connection_capabilities(connection)

        if config.get('model_ids'):
            entries = [{'id': model_id} for model_id in config['model_ids']]
        elif connection.get('type') == 'openai':
            entries = await get_synced_image_models(request, connection, user)
        else:
            entries = [{'id': ''}]

        for entry in entries:
            model_id = entry['id']
            models.append(
                {
                    'id': get_image_model_ref(connection['id'], model_id),
                    'name': model_id or connection.get('name') or connection['id'],
                    'model': model_id,
                    'connection_id': connection['id'],
                    'connection_name': connection.get('name') or connection['id'],
                    # A synced model can do only what both the connection allows and the server says it does.
                    **{
                        capability: capabilities[capability] and entry.get(capability, True)
                        for capability in IMAGE_CAPABILITIES
                    },
                    'connection': connection,
                }
            )
    return models


def get_requested_model(metadata: dict | None, feature: str, meta_key: str) -> str | None:
    """The model a chat asked for: the user's pick, else the chat model's default.

    The pick rides on the feature itself, ``features.<feature> = {'model': ref}``; plain ``true`` means no pick.
    """
    metadata = metadata or {}
    requested = (metadata.get('features') or {}).get(feature)
    if isinstance(requested, dict) and isinstance(requested.get('model'), str) and requested['model']:
        return requested['model']
    model = metadata.get('model') or {}
    return ((model.get('info') or {}).get('meta') or {}).get(meta_key) or None


def get_requested_image_model(metadata: dict | None) -> str | None:
    return get_requested_model(metadata, 'image_generation', 'imageModelId')


async def resolve_image_model(
    request: Request,
    user: UserModel,
    capability: ImageCapability,
    model: str | None = None,
    *,
    strict: bool = False,
) -> tuple[dict, str]:
    """Pick the connection and model to run a request on.

    Order: the requested model (a reference or a bare model id), then the admin's default for
    the capability, then the first model the user can use for it. A requested model the user
    cannot use, or one that cannot do the capability (an edit sent to a generation-only model),
    falls back to the default unless ``strict`` is set, as on the direct API routes.
    """
    models = await get_image_models(request, user)

    def find(value: str | None) -> dict | None:
        if not value:
            return None
        return next((m for m in models if m['id'] == value), None) or next(
            (m for m in models if m['model'] == value), None
        )

    if model:
        requested = find(model)
        if requested and requested[capability]:
            return requested['connection'], requested['model']
        if strict:
            detail = (
                f'Image model "{model}" cannot be used for {capability.replace("_", " ")}'
                if requested
                else f'Image model "{model}" was not found'
            )
            raise HTTPException(status_code=400, detail=detail)
        log.debug('Image model %s is not available to %s for %s; using the default', model, user.id, capability)

    default_key = (
        IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY
        if capability == 'image_generation'
        else IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY
    )
    default = find(await Config.get(default_key))
    if default and default[capability]:
        return default['connection'], default['model']

    fallback = next((m for m in models if m[capability]), None)
    if fallback:
        return fallback['connection'], fallback['model']

    raise HTTPException(
        status_code=400,
        detail=ERROR_MESSAGES.DEFAULT(
            'No image model is available'
            if capability == 'image_generation'
            else 'No image model that can edit images is available'
        ),
    )


# Migration from the single-engine settings


def _legacy_generation_connection(values: dict) -> dict | None:
    connection_type = values.get('image_generation.engine') or 'automatic1111'
    enabled = bool(values.get('image_generation.enable'))
    model = values.get('image_generation.model') or ''
    config: dict[str, Any] = {
        'size': values.get('image_generation.size') or '',
        'steps': values.get('image_generation.steps'),
    }

    if connection_type == 'openai':
        url = values.get('image_generation.openai.api_base_url') or ''
        key = values.get('image_generation.openai.api_key') or ''
        config.update(
            api_version=values.get('image_generation.openai.api_version') or '',
            params=values.get('image_generation.openai.params') or {},
        )
        model = model or DEFAULT_OPENAI_IMAGE_MODEL
        configured = bool(url) and (bool(key) or enabled)
    elif connection_type == 'gemini':
        url = values.get('image_generation.gemini.api_base_url') or ''
        key = values.get('image_generation.gemini.api_key') or ''
        config.update(endpoint_method=values.get('image_generation.gemini.endpoint_method') or '')
        model = model or DEFAULT_GEMINI_IMAGE_MODEL
        configured = bool(url) and (bool(key) or enabled)
    elif connection_type == 'comfyui':
        url = values.get('image_generation.comfyui.base_url') or ''
        key = values.get('image_generation.comfyui.api_key') or ''
        config.update(
            workflow=values.get('image_generation.comfyui.workflow') or '',
            nodes=values.get('image_generation.comfyui.nodes') or [],
        )
        configured = bool(url)
    else:
        connection_type = 'automatic1111'
        url = values.get('image_generation.automatic1111.base_url') or ''
        key = values.get('image_generation.automatic1111.api_auth') or ''
        config.update(params=values.get('image_generation.automatic1111.api_params') or {})
        configured = bool(url)

    if not configured:
        return None

    config.update(model_ids=[model], capabilities={'image_generation': True, 'image_edit': False})
    return {'type': connection_type, 'url': url, 'key': key, 'config': config}


def _legacy_edit_connection(values: dict) -> dict | None:
    connection_type = values.get('images.edit.engine') or 'openai'
    enabled = bool(values.get('images.edit.enable'))
    model = values.get('images.edit.model') or ''
    config: dict[str, Any] = {'edit_size': values.get('images.edit.size') or ''}

    if connection_type == 'openai':
        url = values.get('images.edit.openai.api_base_url') or ''
        key = values.get('images.edit.openai.api_key') or ''
        config.update(api_version=values.get('images.edit.openai.api_version') or '')
        model = model or DEFAULT_OPENAI_IMAGE_MODEL
        configured = bool(url) and (bool(key) or enabled)
    elif connection_type == 'gemini':
        url = values.get('images.edit.gemini.api_base_url') or ''
        key = values.get('images.edit.gemini.api_key') or ''
        # The edit route builds models/{model}:generateContent, so it never worked without a model.
        configured = bool(url) and bool(model) and (bool(key) or enabled)
    elif connection_type == 'comfyui':
        url = values.get('images.edit.comfyui.base_url') or ''
        key = values.get('images.edit.comfyui.api_key') or ''
        config.update(
            edit_workflow=values.get('images.edit.comfyui.workflow') or '',
            edit_nodes=values.get('images.edit.comfyui.nodes') or [],
        )
        configured = bool(url)
    else:
        return None

    if not configured:
        return None

    config.update(model_ids=[model], capabilities={'image_generation': False, 'image_edit': True})
    return {'type': connection_type, 'url': url, 'key': key, 'config': config}


LEGACY_IMAGE_CONFIG_KEYS = (
    'image_generation.enable',
    'image_generation.engine',
    'image_generation.model',
    'image_generation.size',
    'image_generation.steps',
    'image_generation.openai.api_base_url',
    'image_generation.openai.api_key',
    'image_generation.openai.api_version',
    'image_generation.openai.params',
    'image_generation.gemini.api_base_url',
    'image_generation.gemini.api_key',
    'image_generation.gemini.endpoint_method',
    'image_generation.comfyui.base_url',
    'image_generation.comfyui.api_key',
    'image_generation.comfyui.workflow',
    'image_generation.comfyui.nodes',
    'image_generation.automatic1111.base_url',
    'image_generation.automatic1111.api_auth',
    'image_generation.automatic1111.api_params',
    'images.edit.enable',
    'images.edit.engine',
    'images.edit.model',
    'images.edit.size',
    'images.edit.openai.api_base_url',
    'images.edit.openai.api_key',
    'images.edit.openai.api_version',
    'images.edit.gemini.api_base_url',
    'images.edit.gemini.api_key',
    'images.edit.comfyui.base_url',
    'images.edit.comfyui.api_key',
    'images.edit.comfyui.workflow',
    'images.edit.comfyui.nodes',
)

LEGACY_IMAGE_CONNECTION_NAMES = {
    'openai': 'OpenAI',
    'gemini': 'Gemini',
    'comfyui': 'ComfyUI',
    'automatic1111': 'AUTOMATIC1111',
}


async def migrate_legacy_image_config() -> list[dict]:
    """Turn the single generation and edit engine settings into image connections, once.

    The connections key is only written here or by an admin, so its absence marks a deployment
    that has not been migrated. Both old engines keep working, with everyone who could use them
    before keeping access.
    """
    connections = await Config.get(IMAGE_CONNECTIONS_CONFIG_KEY)
    if connections is not None:
        return connections

    values = await Config.get_many(*LEGACY_IMAGE_CONFIG_KEYS)
    generation = _legacy_generation_connection(values)
    edit = _legacy_edit_connection(values)

    folded_edit_model = None
    if (
        generation
        and edit
        and (generation['type'], generation['url'], generation['key'])
        == (
            edit['type'],
            edit['url'],
            edit['key'],
        )
    ):
        # Same backend for both: one connection, with the edit model and settings folded in.
        generation_model = generation['config']['model_ids'][0]
        folded_edit_model = edit['config']['model_ids'][0]
        for key, value in edit['config'].items():
            if key not in ('model_ids', 'capabilities'):
                generation['config'].setdefault(key, value)
        generation['config']['capabilities'] = {'image_generation': True, 'image_edit': True}
        if folded_edit_model != generation_model:
            generation['config']['model_ids'].append(folded_edit_model)
        edit = None

    connections = []
    defaults = {IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY: '', IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY: ''}
    for legacy, default_key, suffix in (
        (generation, IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY, ''),
        (edit, IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY, ' (edit)'),
    ):
        if legacy is None:
            continue
        legacy['config']['access_grants'] = PUBLIC_ACCESS_GRANTS
        connection = normalize_image_connection(
            {**legacy, 'name': f'{LEGACY_IMAGE_CONNECTION_NAMES[legacy["type"]]}{suffix}'}
        )
        connections.append(connection)
        # An empty legacy model (ComfyUI, AUTOMATIC1111) becomes the connection's default model.
        defaults[default_key] = get_image_model_ref(connection['id'], legacy['config']['model_ids'][0])

    if folded_edit_model is not None:
        defaults[IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY] = get_image_model_ref(connections[0]['id'], folded_edit_model)

    await Config.upsert({IMAGE_CONNECTIONS_CONFIG_KEY: connections, **defaults})
    if connections:
        log.info('Migrated image generation settings to %d image connection(s)', len(connections))
    return connections
