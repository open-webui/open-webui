from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Optional, Union
from urllib.parse import urlparse

import aiohttp
from aiocache import cached
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.config import UPLOAD_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    FORWARD_SESSION_INFO_HEADER_CHAT_ID,
    MODELS_CACHE_TTL,
)
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.models import Models
from open_webui.models.users import UserModel
from open_webui.utils.access_control import check_model_access
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_custom_headers, include_user_info_headers
from open_webui.utils.misc import calculate_sha256
from open_webui.utils.payload import (
    apply_model_params_to_body_ollama,
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.session_pool import cleanup_response, get_session, stream_wrapper

log = logging.getLogger(__name__)

# Headers that become stale after aiohttp auto-decompresses the upstream
# response body.  Forwarding them verbatim causes desktop / programmatic
# clients to attempt decompression of an already-decoded payload, resulting
# in ZlibError.  See https://github.com/aio-libs/aiohttp/issues/4462.
_STRIP_PROXY_HEADERS = frozenset({'Content-Encoding', 'Content-Length', 'Transfer-Encoding'})


def _clean_proxy_headers(raw_headers) -> dict:
    """Return a copy of *raw_headers* with stale encoding headers removed."""
    return {k: v for k, v in raw_headers.items() if k not in _STRIP_PROXY_HEADERS}


async def send_get_request(
    url: str,
    key: str | None = None,
    user: UserModel | None = None,
):
    """Issue a GET request to an Ollama backend and return JSON, or *None* on failure."""
    try:
        session = await get_session()
        headers: dict = {
            'Content-Type': 'application/json',
        }
        if key:
            headers['Authorization'] = f'Bearer {key}'
        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
            headers = include_user_info_headers(headers, user)

        async with session.get(
            url,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as r:
            return await r.json()
    except Exception as exc:
        log.error(f'Connection error: {exc}')
        return None


async def send_request(
    url: str,
    method: str = 'POST',
    *,
    payload: Union[str, bytes | None] = None,
    key: str | None = None,
    user: UserModel = None,
    stream: bool = False,
    content_type: str | None = None,
    metadata: dict | None = None,
    api_config: dict | None = None,
    request: Request | None = None,
):
    r = None
    streaming = False
    try:
        session = await get_session()

        headers = {
            'Content-Type': 'application/json',
            **({'Authorization': f'Bearer {key}'} if key else {}),
        }

        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
            headers = include_user_info_headers(headers, user)
            if metadata and metadata.get('chat_id'):
                headers[FORWARD_SESSION_INFO_HEADER_CHAT_ID] = metadata.get('chat_id')

        # Custom per-connection headers last so admin-set headers take precedence.
        if api_config and api_config.get('headers'):
            headers.update(get_custom_headers(api_config['headers'], user, metadata, request=request))

        r = await session.request(
            method,
            url,
            data=payload,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        if not r.ok:
            try:
                res = await r.json()
                if 'error' in res:
                    raise HTTPException(status_code=r.status, detail=res['error'])
            except HTTPException:
                raise
            except Exception as e:
                log.error(f'Failed to parse error response: {e}')
            raise HTTPException(
                status_code=r.status,
                detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
            )

        r.raise_for_status()

        if stream:
            response_headers = _clean_proxy_headers(r.headers)
            if content_type:
                response_headers['Content-Type'] = content_type

            streaming = True
            return StreamingResponse(
                stream_wrapper(r),
                status_code=r.status,
                headers=response_headers,
            )
        else:
            try:
                return await r.json()
            except Exception:
                return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=f'Ollama: {e}' if str(e) else ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
        )
    finally:
        if not streaming:
            await cleanup_response(r)


def get_api_key(idx, url, configs):
    parsed_url = urlparse(url)
    base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
    return configs.get(str(idx), configs.get(base_url, {})).get('key', None)  # Legacy support


##########################################
#
# API routes
#
##########################################

router = APIRouter()

OLLAMA_CONFIG_KEYS = {
    'ENABLE_OLLAMA_API': 'ollama.enable',
    'OLLAMA_BASE_URLS': 'ollama.base_urls',
    'OLLAMA_API_CONFIGS': 'ollama.api_configs',
}


async def get_ollama_config_values() -> dict:
    values = await Config.get_many(*OLLAMA_CONFIG_KEYS.values())
    return {field: values[storage_key] for field, storage_key in OLLAMA_CONFIG_KEYS.items() if storage_key in values}


async def get_ollama_runtime_config() -> tuple[bool, list[str], dict]:
    values = await Config.get_many('ollama.enable', 'ollama.base_urls', 'ollama.api_configs')
    return (
        values.get('ollama.enable'),
        values.get('ollama.base_urls') or [],
        values.get('ollama.api_configs') or {},
    )


async def get_ollama_connection(idx: int) -> tuple[str, dict, str | None]:
    _, base_urls, api_configs = await get_ollama_runtime_config()
    url = base_urls[idx]
    return url, resolve_api_config(api_configs, idx, url), get_api_key(idx, url, api_configs)


@router.head('/')
@router.get('/')
async def get_status() -> dict:
    """Health-check endpoint."""
    return {'status': True}


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str | None = None


@router.post('/verify')
async def verify_connection(
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    """Verify that an Ollama backend at *form_data.url* is reachable."""
    try:
        session = await get_session()
        headers: dict = {}
        if form_data.key:
            headers['Authorization'] = f'Bearer {form_data.key}'
        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
            headers = include_user_info_headers(headers, user)

        async with session.get(
            f'{form_data.url}/api/version',
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as r:
            if r.status != 200:
                detail = f'HTTP Error: {r.status}'
                res = await r.json()
                if 'error' in res:
                    detail = f'External Error: {res["error"]}'
                raise Exception(detail)

            return await r.json()
    except aiohttp.ClientError as exc:
        log.exception(f'Client error: {exc}')
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR)
    except Exception as exc:
        log.exception(f'Unexpected error: {exc}')
        raise HTTPException(status_code=500, detail=f'Unexpected error: {exc}')


@router.get('/config')
async def get_config(
    request: Request,
    user=Depends(get_admin_user),
) -> dict:
    """Return the current Ollama connection configuration."""
    return await get_ollama_config_values()


class OllamaConfigForm(BaseModel):
    """Payload for updating the Ollama connection configuration."""

    ENABLE_OLLAMA_API: bool | None = None
    OLLAMA_BASE_URLS: list[str]
    OLLAMA_API_CONFIGS: dict


@router.post('/config/update')
async def update_config(
    request: Request,
    form_data: OllamaConfigForm,
    user=Depends(get_admin_user),
) -> dict:
    """Persist updated Ollama connection settings."""
    valid_keys = {str(i) for i in range(len(form_data.OLLAMA_BASE_URLS))}
    api_configs = {k: v for k, v in form_data.OLLAMA_API_CONFIGS.items() if k in valid_keys}

    await Config.upsert(
        {
            'ollama.enable': form_data.ENABLE_OLLAMA_API,
            'ollama.base_urls': form_data.OLLAMA_BASE_URLS,
            'ollama.api_configs': api_configs,
        }
    )
    await publish_event(
        request,
        EVENTS.MODEL_PROVIDER_CONFIG_UPDATED,
        actor=user,
        subject_id='ollama',
        subject_type='model.provider_config',
        data={
            'provider': 'ollama',
            'enabled': form_data.ENABLE_OLLAMA_API,
            'base_url_count': len(form_data.OLLAMA_BASE_URLS),
        },
    )
    return {
        'ENABLE_OLLAMA_API': form_data.ENABLE_OLLAMA_API,
        'OLLAMA_BASE_URLS': form_data.OLLAMA_BASE_URLS,
        'OLLAMA_API_CONFIGS': api_configs,
    }


def merge_models_lists(model_lists) -> list[dict]:
    """De-duplicate model entries across multiple Ollama backends, tracking which URL index hosts each model."""
    merged: dict[str, dict] = {}
    for idx, entries in enumerate(model_lists):
        if entries is None:
            continue
        for entry in entries:
            model_id = entry.get('model')
            if model_id is None:
                continue
            if model_id not in merged:
                entry['urls'] = [idx]
                merged[model_id] = entry
            else:
                merged[model_id]['urls'].append(idx)
    return list(merged.values())


def resolve_api_config(api_configs: dict, idx: int, url: str) -> dict:
    """Look up the API config for a backend by numeric index, falling back to URL key (legacy)."""
    return api_configs.get(str(idx), api_configs.get(url, {}))


@cached(
    ttl=MODELS_CACHE_TTL,
    # key_builder (not key) is the per-call hook in aiocache 0.12; `key=` is a
    # static key, so a `key=lambda` collapsed every caller to one shared entry.
    key_builder=lambda _func, request, user=None: f'ollama_all_models_{user.id}' if user else 'ollama_all_models',
)
async def get_all_models(request: Request, user: UserModel | None = None):
    """Aggregate model tags from every enabled Ollama backend."""
    log.info('get_all_models()')

    if not await Config.get('ollama.enable'):
        models_dict: dict = {'models': []}
        request.app.state.OLLAMA_MODELS = {}
        return models_dict

    # Fan-out tag requests to every backend
    tasks = []
    base_urls = await Config.get('ollama.base_urls', [])
    api_configs = await Config.get('ollama.api_configs', {})
    for idx, url in enumerate(base_urls):
        api_config = resolve_api_config(api_configs, idx, url)
        if not api_config:
            tasks.append(send_get_request(f'{url}/api/tags', user=user))
        elif api_config.get('enable', True):
            tasks.append(send_get_request(f'{url}/api/tags', api_config.get('key'), user=user))
        else:
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*tasks)

    # Track which backends failed so we can skip them for /api/ps
    failed_idxs: set[int] = set()

    # Post-process each response: apply prefix_id, tags, model filtering
    for idx, response in enumerate(responses):
        if not response:
            failed_idxs.add(idx)
            continue
        url = base_urls[idx]
        api_config = resolve_api_config(api_configs, idx, url)

        connection_type = api_config.get('connection_type', 'local')
        prefix_id = api_config.get('prefix_id')
        allowed_tags = api_config.get('tags', [])
        allowed_model_ids = api_config.get('model_ids', [])

        if allowed_model_ids and 'models' in response:
            response['models'] = [m for m in response['models'] if m['model'] in allowed_model_ids]

        for m in response.get('models', []):
            if prefix_id:
                m['model'] = f'{prefix_id}.{m["model"]}'
            if allowed_tags:
                m['tags'] = allowed_tags
            if connection_type:
                m['connection_type'] = connection_type

    models_dict = {'models': merge_models_lists(r.get('models', []) if r else None for r in responses)}

    # Annotate with expiry info from loaded-model state
    try:
        loaded = await get_ollama_loaded_models(request, user=user, skip_idxs=failed_idxs)
        expires_map = {m['model']: m['expires_at'] for m in loaded['models'] if 'expires_at' in m}
        for m in models_dict['models']:
            if m['model'] in expires_map:
                dt = datetime.fromisoformat(expires_map[m['model']])
                m['expires_at'] = int(dt.timestamp())
    except Exception as exc:
        log.debug(f'Failed to get loaded models: {exc}')

    request.app.state.OLLAMA_MODELS = {m['model']: m for m in models_dict['models']}
    return models_dict


async def get_filtered_models(models, user, db=None):
    """Return only the models the given *user* is allowed to access."""
    model_ids = [m['model'] for m in models.get('models', [])]
    model_infos = {mi.id: mi for mi in await Models.get_models_by_ids(model_ids, db=db)}
    user_group_ids = {g.id for g in await Groups.get_groups_by_member_id(user.id, db=db)}

    accessible_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='model',
        resource_ids=list(model_infos.keys()),
        permission='read',
        user_group_ids=user_group_ids,
        db=db,
    )
    return [
        m
        for m in models.get('models', [])
        if (mi := model_infos.get(m['model'])) and (user.id == mi.user_id or mi.id in accessible_ids)
    ]


@router.get('/api/tags')
@router.get('/api/tags/{url_idx}')
async def get_ollama_tags(
    request: Request,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """List Ollama model tags, optionally from a specific backend."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    if url_idx is None:
        result = await get_all_models(request, user=user)
    else:
        url = (await Config.get('ollama.base_urls', []))[url_idx]
        key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))
        result = await send_request(f'{url}/api/tags', 'GET', key=key, user=user)

    if user.role == 'user' and not BYPASS_MODEL_ACCESS_CONTROL:
        result['models'] = await get_filtered_models(result, user)

    return result


@router.get('/api/ps')
async def get_ollama_loaded_models(
    request: Request,
    user=Depends(get_admin_user),
    skip_idxs: set[int] | None = None,
) -> dict:
    """List models currently loaded in Ollama memory across all backends."""
    if not await Config.get('ollama.enable'):
        return {'models': []}

    tasks = []
    base_urls = await Config.get('ollama.base_urls', [])
    api_configs = await Config.get('ollama.api_configs', {})
    for idx, url in enumerate(base_urls):
        if skip_idxs and idx in skip_idxs:
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))
            continue
        api_config = resolve_api_config(api_configs, idx, url)
        if not api_config:
            tasks.append(send_get_request(f'{url}/api/ps', user=user))
        elif api_config.get('enable', True):
            tasks.append(send_get_request(f'{url}/api/ps', api_config.get('key'), user=user))
        else:
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*tasks)

    for idx, response in enumerate(responses):
        if not response:
            continue
        api_config = resolve_api_config(api_configs, idx, base_urls[idx])
        prefix_id = api_config.get('prefix_id')
        if prefix_id:
            for m in response.get('models', []):
                m['model'] = f'{prefix_id}.{m["model"]}'

    return {'models': merge_models_lists(r.get('models', []) if r else None for r in responses)}


@router.get('/api/version')
@router.get('/api/version/{url_idx}')
async def get_ollama_versions(
    request: Request,
    url_idx: int | None = None,
):
    """Return the lowest Ollama version across all configured backends."""
    if not await Config.get('ollama.enable'):
        return {'version': False}

    if url_idx is not None:
        url = (await Config.get('ollama.base_urls', []))[url_idx]
        return await send_request(f'{url}/api/version', 'GET')

    # Fan-out to every enabled backend
    tasks = []
    for idx, url in enumerate(await Config.get('ollama.base_urls', [])):
        api_config = (await Config.get('ollama.api_configs', {})).get(
            str(idx),
            (await Config.get('ollama.api_configs', {})).get(url, {}),
        )
        if api_config.get('enable', True):
            tasks.append(send_get_request(f'{url}/api/version', api_config.get('key')))

    raw = await asyncio.gather(*tasks)
    valid = [r for r in raw if r is not None]

    if not valid:
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES.OLLAMA_NOT_FOUND)

    lowest = min(
        valid,
        key=lambda v: tuple(map(int, re.sub(r'^v|-.*', '', v['version']).split('.'))),
    )
    return {'version': lowest['version']}


class ModelNameForm(BaseModel):
    """Generic form carrying an optional model identifier."""

    model: str | None = None
    model_config = ConfigDict(extra='allow')


@router.post('/api/unload')
async def unload_model(
    request: Request,
    form_data: ModelNameForm,
    user=Depends(get_admin_user),
):
    form_data = form_data.model_dump(exclude_none=True)
    model = form_data.get('model', form_data.get('name'))

    if not model:
        raise HTTPException(status_code=400, detail='Missing name of the model to unload.')

    # Refresh/load models if needed, get mapping from name to URLs
    await get_all_models(request, user=user)
    models = request.app.state.OLLAMA_MODELS

    if model not in models:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model))
    url_indices = models[model]['urls']

    # Send unload to ALL url_indices
    results = []
    errors = []
    for idx in url_indices:
        url = (await Config.get('ollama.base_urls', []))[idx]
        api_config = (await Config.get('ollama.api_configs', {})).get(
            str(idx), (await Config.get('ollama.api_configs', {})).get(url, {})
        )
        key = get_api_key(idx, url, (await Config.get('ollama.api_configs', {})))

        prefix_id = api_config.get('prefix_id', None)
        if prefix_id and model.startswith(f'{prefix_id}.'):
            model = model[len(f'{prefix_id}.') :]

        payload = {'model': model, 'keep_alive': 0, 'prompt': ''}

        try:
            res = await send_request(
                f'{url}/api/generate',
                payload=json.dumps(payload),
                key=key,
                user=user,
            )
            results.append({'url_idx': idx, 'success': True, 'response': res})
        except Exception as e:
            log.exception(f'Failed to unload model on node {idx}: {e}')
            errors.append({'url_idx': idx, 'success': False, 'error': str(e)})

    if len(errors) > 0:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to unload model on {len(errors)} nodes: {errors}',
        )

    return {'status': True}


@router.post('/api/pull')
@router.post('/api/pull/{url_idx}')
async def pull_model(
    request: Request,
    form_data: ModelNameForm,
    url_idx: int = 0,
    user=Depends(get_admin_user),
):
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    form_data = form_data.model_dump(exclude_none=True)
    form_data['model'] = form_data.get('model', form_data.get('name'))

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    log.info(f'url: {url}')

    # Admins may pull from any registry
    return await send_request(
        f'{url}/api/pull',
        payload=json.dumps({**form_data, 'insecure': True}),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=True,
    )


class PushModelForm(BaseModel):
    """Payload for pushing a model to a registry."""

    model: str
    insecure: bool | None = None
    stream: bool | None = None


@router.delete('/api/push')
@router.delete('/api/push/{url_idx}')
async def push_model(
    request: Request,
    form_data: PushModelForm,
    url_idx: int | None = None,
    user=Depends(get_admin_user),
):
    """Push a local model to a remote registry."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    if url_idx is None:
        await get_all_models(request, user=user)
        models = request.app.state.OLLAMA_MODELS
        if form_data.model not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model))
        url_idx = models[form_data.model]['urls'][0]

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    log.debug(f'url: {url}')

    return await send_request(
        f'{url}/api/push',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=True,
    )


class CreateModelForm(BaseModel):
    """Payload for creating a new model via Modelfile."""

    model: str | None = None
    stream: bool | None = None
    path: str | None = None
    model_config = ConfigDict(extra='allow')


@router.post('/api/create')
@router.post('/api/create/{url_idx}')
async def create_model(
    request: Request,
    form_data: CreateModelForm,
    url_idx: int = 0,
    user=Depends(get_admin_user),
):
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    log.debug(f'form_data: {form_data}')
    url = (await Config.get('ollama.base_urls', []))[url_idx]

    return await send_request(
        f'{url}/api/create',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=True,
    )


class CopyModelForm(BaseModel):
    """Payload for duplicating an existing model under a new name."""

    source: str
    destination: str


@router.post('/api/copy')
@router.post('/api/copy/{url_idx}')
async def copy_model(
    request: Request,
    form_data: CopyModelForm,
    url_idx: int | None = None,
    user=Depends(get_admin_user),
):
    """Duplicate an existing model under a new name."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    if url_idx is None:
        await get_all_models(request, user=user)
        models = request.app.state.OLLAMA_MODELS
        if form_data.source not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.source))
        url_idx = models[form_data.source]['urls'][0]

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))

    await send_request(
        f'{url}/api/copy',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=key,
        user=user,
    )
    await publish_event(
        request,
        EVENTS.MODEL_PROVIDER_MODEL_CREATED,
        actor=user,
        subject_id=form_data.destination,
        data={'provider': 'ollama', 'source': form_data.source, 'url_idx': url_idx},
    )
    return True


@router.delete('/api/delete')
@router.delete('/api/delete/{url_idx}')
async def delete_model(
    request: Request,
    form_data: ModelNameForm,
    url_idx: int | None = None,
    user=Depends(get_admin_user),
):
    """Remove a model from an Ollama backend."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    payload = form_data.model_dump(exclude_none=True)
    payload['model'] = payload.get('model', payload.get('name'))
    model = payload.get('model')

    if url_idx is None:
        await get_all_models(request, user=user)
        models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model))
        url_idx = models[model]['urls'][0]

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))

    await send_request(
        f'{url}/api/delete',
        'DELETE',
        payload=json.dumps(payload),
        key=key,
        user=user,
    )
    await publish_event(
        request,
        EVENTS.MODEL_PROVIDER_MODEL_DELETED,
        actor=user,
        subject_id=model,
        data={'provider': 'ollama', 'url_idx': url_idx},
    )
    return True


@router.post('/api/show')
async def show_model_info(
    request: Request,
    form_data: ModelNameForm,
    user=Depends(get_verified_user),
):
    """Retrieve model metadata from the Ollama backend."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    payload = form_data.model_dump(exclude_none=True)
    payload['model'] = payload.get('model', payload.get('name'))
    model = payload.get('model')

    await check_model_access(user, await Models.get_model_by_id(model), BYPASS_MODEL_ACCESS_CONTROL)

    await get_all_models(request, user=user)
    models = request.app.state.OLLAMA_MODELS

    if model not in models:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model))

    url_idx = random.choice(models[model]['urls'])
    url = (await Config.get('ollama.base_urls', []))[url_idx]
    key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))

    return await send_request(
        f'{url}/api/show',
        payload=json.dumps(payload),
        key=key,
        user=user,
    )


class GenerateEmbedForm(BaseModel):
    """Payload for the newer /api/embed endpoint (batch-capable)."""

    model: str
    input: list[str] | str
    truncate: bool | None = None
    options: dict | None = None
    keep_alive: Union[int, str | None] = None
    model_config = ConfigDict(extra='allow')


@router.post('/api/embed')
@router.post('/api/embed/{url_idx}')
async def embed(
    request: Request,
    form_data: GenerateEmbedForm,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """Generate embeddings via the Ollama /api/embed endpoint."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    log.info(f'generate_ollama_batch_embeddings {form_data}')
    await check_model_access(user, await Models.get_model_by_id(form_data.model), BYPASS_MODEL_ACCESS_CONTROL)
    await validate_ollama_backend_idx(request, form_data.model, url_idx, user)

    if url_idx is None:
        model = form_data.model
        models = request.app.state.OLLAMA_MODELS
        if not models or model not in models:
            await get_all_models(request, user=user)
            models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model))
        url_idx = random.choice(models[model]['urls'])

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    api_config = (await Config.get('ollama.api_configs', {})).get(
        str(url_idx),
        (await Config.get('ollama.api_configs', {})).get(url, {}),
    )
    key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        form_data.model = form_data.model.replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/api/embed',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=key,
        user=user,
    )


class GenerateEmbeddingsForm(BaseModel):
    """Payload for the legacy /api/embeddings endpoint (single-prompt)."""

    model: str
    prompt: str
    options: dict | None = None
    keep_alive: Union[int, str | None] = None


@router.post('/api/embeddings')
@router.post('/api/embeddings/{url_idx}')
async def embeddings(
    request: Request,
    form_data: GenerateEmbeddingsForm,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """Generate embeddings via the legacy Ollama /api/embeddings endpoint."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    log.info(f'generate_ollama_embeddings {form_data}')
    await check_model_access(user, await Models.get_model_by_id(form_data.model), BYPASS_MODEL_ACCESS_CONTROL)
    await validate_ollama_backend_idx(request, form_data.model, url_idx, user)

    if url_idx is None:
        model = form_data.model
        models = request.app.state.OLLAMA_MODELS
        if not models or model not in models:
            await get_all_models(request, user=user)
            models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model))
        url_idx = random.choice(models[model]['urls'])

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    api_config = (await Config.get('ollama.api_configs', {})).get(
        str(url_idx),
        (await Config.get('ollama.api_configs', {})).get(url, {}),
    )
    key = get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {})))

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        form_data.model = form_data.model.replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/api/embeddings',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=key,
        user=user,
    )


class GenerateCompletionForm(BaseModel):
    """Payload for the Ollama /api/generate endpoint."""

    model: str
    prompt: str | None = None
    suffix: str | None = None
    images: list[str | None] = None
    format: Union[dict, str | None] = None
    options: dict | None = None
    system: str | None = None
    template: str | None = None
    context: list[int | None] = None
    stream: bool | None = True
    raw: bool | None = None
    keep_alive: Union[int, str | None] = None


@router.post('/api/generate')
@router.post('/api/generate/{url_idx}')
async def generate_completion(
    request: Request,
    form_data: GenerateCompletionForm,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """Run text completion via Ollama /api/generate."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    await check_model_access(user, await Models.get_model_by_id(form_data.model), BYPASS_MODEL_ACCESS_CONTROL)
    await validate_ollama_backend_idx(request, form_data.model, url_idx, user)

    if url_idx is None:
        await get_all_models(request, user=user)
        models = request.app.state.OLLAMA_MODELS
        model = form_data.model
        if model not in models:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model))
        url_idx = random.choice(models[model]['urls'])

    url = (await Config.get('ollama.base_urls', []))[url_idx]
    api_config = (await Config.get('ollama.api_configs', {})).get(
        str(url_idx),
        (await Config.get('ollama.api_configs', {})).get(url, {}),
    )

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        form_data.model = form_data.model.replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/api/generate',
        payload=form_data.model_dump_json(exclude_none=True).encode(),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=True,
    )


class ChatMessage(BaseModel):
    """A single message in an Ollama chat conversation."""

    role: str
    content: str | None = None
    tool_calls: list[dict | None] = None
    images: list[str | None] = None
    model_config = ConfigDict(extra='allow')

    @validator('content', pre=True)
    @classmethod
    def check_at_least_one_field(cls, field_value, values, **kwargs):
        if field_value is None and ('tool_calls' not in values or values['tool_calls'] is None):
            raise ValueError("At least one of 'content' or 'tool_calls' must be provided")
        return field_value


class GenerateChatCompletionForm(BaseModel):
    """Payload for the Ollama /api/chat endpoint."""

    model: str
    messages: list[ChatMessage]
    format: Union[dict, str | None] = None
    options: dict | None = None
    template: str | None = None
    stream: bool | None = True
    keep_alive: Union[int, str | None] = None
    tools: list[dict | None] = None
    model_config = ConfigDict(extra='allow')


async def validate_ollama_backend_idx(request: Request, model: str, url_idx: int | None, user) -> None:
    # A caller-supplied url_idx must point to a backend the model is actually
    # served from; the None path is already constrained to that allow-list.
    if url_idx is None or user is None or getattr(user, 'role', None) == 'admin' or BYPASS_MODEL_ACCESS_CONTROL:
        return
    models = request.app.state.OLLAMA_MODELS
    if not models or model not in models:
        await get_all_models(request, user=user)
        models = request.app.state.OLLAMA_MODELS
    if url_idx not in (models.get(model) or {}).get('urls', []):
        raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)


async def get_ollama_url(request: Request, model: str, url_idx: int | None = None, user=None):
    await validate_ollama_backend_idx(request, model, url_idx, user)
    if url_idx is None:
        models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model),
            )
        url_idx = random.choice(models[model].get('urls', []))
    url = (await Config.get('ollama.base_urls', []))[url_idx]
    return url, url_idx


@router.post('/api/chat')
@router.post('/api/chat/{url_idx}')
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    url_idx: int | None = None,
    user=Depends(get_verified_user),  # noqa: B008
):
    """Forward a chat completion request to an Ollama backend."""
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations (get_model_by_id, AccessGrants.has_access) manage their own short-lived sessions.
    # This prevents holding a connection during the entire LLM call (30-60+ seconds),
    # which would exhaust the connection pool under concurrent load.

    # bypass_filter and bypass_system_prompt are read from request.state to prevent
    # external clients from setting them via query parameter. Only internal
    # server-side callers (e.g. utils/chat.py) should set
    # request.state.bypass_filter / request.state.bypass_system_prompt = True.
    bypass_filter = getattr(request.state, 'bypass_filter', False)
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True
    bypass_system_prompt = getattr(request.state, 'bypass_system_prompt', False)

    metadata = form_data.pop('metadata', None)
    try:
        form_data = GenerateChatCompletionForm(**form_data)
    except Exception as exc:
        log.exception(exc)
        raise HTTPException(status_code=400, detail=str(exc))

    if isinstance(form_data, BaseModel):
        payload = {**form_data.model_dump(exclude_none=True)}

    payload.pop('metadata', None)

    model_id = payload['model']
    model_info = await Models.get_model_by_id(model_id)

    if model_info is not None:
        if model_info.base_model_id:
            base_model_id = request.base_model_id if hasattr(request, 'base_model_id') else model_info.base_model_id
            payload['model'] = base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop('system', None)
            payload = apply_model_params_to_body_ollama(params, payload)
            if not bypass_system_prompt:
                payload = await apply_system_prompt_to_body(system, payload, metadata, user)

        await check_model_access(user, model_info, bypass_filter)
    else:
        await check_model_access(user, None, bypass_filter)

    url, url_idx = await get_ollama_url(request, payload['model'], url_idx, user)
    api_config = resolve_api_config((await Config.get('ollama.api_configs', {})), url_idx, url)

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/api/chat',
        payload=json.dumps(payload),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=form_data.stream,
        content_type='application/x-ndjson',
        metadata=metadata,
        api_config=api_config,
        request=request,
    )


# TODO: we should update this part once Ollama supports other types
class OpenAIChatMessageContent(BaseModel):
    """Content block within an OpenAI-style chat message."""

    type: str
    model_config = ConfigDict(extra='allow')


class OpenAIChatMessage(BaseModel):
    """A single message in an OpenAI-compatible chat request."""

    role: str
    content: Union[str | None, list[OpenAIChatMessageContent]]
    model_config = ConfigDict(extra='allow')


class OpenAIChatCompletionForm(BaseModel):
    """Payload for the OpenAI-compatible /v1/chat/completions proxy."""

    model: str
    messages: list[OpenAIChatMessage]
    model_config = ConfigDict(extra='allow')


class OpenAICompletionForm(BaseModel):
    """Payload for the OpenAI-compatible /v1/completions proxy."""

    model: str
    prompt: str
    model_config = ConfigDict(extra='allow')


@router.post('/v1/completions')
@router.post('/v1/completions/{url_idx}')
async def generate_openai_completion(
    request: Request,
    form_data: dict,
    url_idx: int | None = None,
    user=Depends(get_verified_user),  # noqa: B008
):
    """Forward a text completion request via the OpenAI-compatible proxy."""
    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations (get_model_by_id, AccessGrants.has_access) manage their own short-lived sessions.
    # This prevents holding a connection during the entire LLM call (30-60+ seconds),
    # which would exhaust the connection pool under concurrent load.
    metadata = form_data.pop('metadata', None)

    try:
        form_data = OpenAICompletionForm(**form_data)
    except Exception as exc:
        log.exception(exc)
        raise HTTPException(status_code=400, detail=str(exc))

    payload = {**form_data.model_dump(exclude_none=True, exclude=['metadata'])}
    payload.pop('metadata', None)

    model_id = form_data.model
    model_info = await Models.get_model_by_id(model_id)
    if model_info is not None:
        if model_info.base_model_id:
            payload['model'] = model_info.base_model_id
        params = model_info.params.model_dump()
        if params:
            payload = apply_model_params_to_body_openai(params, payload)
        await check_model_access(user, model_info)
    else:
        await check_model_access(user, None)

    url, url_idx = await get_ollama_url(request, payload['model'], url_idx, user)
    api_config = resolve_api_config((await Config.get('ollama.api_configs', {})), url_idx, url)

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/v1/completions',
        payload=json.dumps(payload),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=payload.get('stream', False),
        metadata=metadata,
        api_config=api_config,
        request=request,
    )


@router.post('/v1/chat/completions')
@router.post('/v1/chat/completions/{url_idx}')
async def generate_openai_chat_completion(
    request: Request,
    form_data: dict,
    url_idx: int | None = None,
    user=Depends(get_verified_user),  # noqa: B008
):
    """Forward a chat completion request via the OpenAI-compatible proxy."""
    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations (get_model_by_id, AccessGrants.has_access) manage their own short-lived sessions.
    # This prevents holding a connection during the entire LLM call (30-60+ seconds),
    # which would exhaust the connection pool under concurrent load.
    metadata = form_data.pop('metadata', None)

    try:
        form_data = OpenAIChatCompletionForm(**form_data)
    except Exception as exc:
        log.exception(exc)
        raise HTTPException(status_code=400, detail=str(exc))

    payload = {**form_data.model_dump(exclude_none=True, exclude=['metadata'])}
    payload.pop('metadata', None)

    model_id = form_data.model
    model_info = await Models.get_model_by_id(model_id)
    if model_info is not None:
        if model_info.base_model_id:
            payload['model'] = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop('system', None)
            payload = apply_model_params_to_body_openai(params, payload)
            payload = await apply_system_prompt_to_body(system, payload, metadata, user)

        await check_model_access(user, model_info)
    else:
        await check_model_access(user, None)

    url, url_idx = await get_ollama_url(request, payload['model'], url_idx, user)
    api_config = resolve_api_config((await Config.get('ollama.api_configs', {})), url_idx, url)

    prefix_id = api_config.get('prefix_id')
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/v1/chat/completions',
        payload=json.dumps(payload),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=payload.get('stream', False),
        metadata=metadata,
        api_config=api_config,
        request=request,
    )


@router.post('/v1/messages')
@router.post('/v1/messages/{url_idx}')
async def generate_anthropic_messages(
    request: Request,
    form_data: dict,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """
    Proxy for Ollama's Anthropic-compatible /v1/messages endpoint.

    Forwards the request as-is to the Ollama backend, applying the same
    model resolution, access control, and prefix_id handling used by
    the OpenAI-compatible /v1/chat/completions proxy.

    See https://docs.ollama.com/api/anthropic-compatibility
    """
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    payload = {**form_data}
    model_id = payload.get('model', '')

    model_info = await Models.get_model_by_id(model_id)
    if model_info:
        if model_info.base_model_id:
            payload['model'] = model_info.base_model_id

        await check_model_access(user, model_info)
    else:
        await check_model_access(user, None)

    url, url_idx = await get_ollama_url(request, payload['model'], url_idx, user)
    api_config = (await Config.get('ollama.api_configs', {})).get(
        str(url_idx),
        (await Config.get('ollama.api_configs', {})).get(url, {}),  # Legacy support
    )

    prefix_id = api_config.get('prefix_id', None)
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/v1/messages',
        payload=json.dumps(payload),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=payload.get('stream', False),
        content_type='text/event-stream' if payload.get('stream', False) else None,
        api_config=api_config,
        request=request,
    )


class ResponsesForm(BaseModel):
    model: str

    model_config = ConfigDict(extra='allow')


@router.post('/v1/responses')
@router.post('/v1/responses/{url_idx}')
async def generate_responses(
    request: Request,
    form_data: ResponsesForm,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
):
    """
    Proxy for Ollama's OpenAI-compatible /v1/responses endpoint.

    Forwards the request as-is to the Ollama backend, applying the same
    model resolution, access control, and prefix_id handling used by
    the OpenAI-compatible /v1/chat/completions proxy.

    See https://ollama.com/blog/responses-api
    """
    if not await Config.get('ollama.enable'):
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES.OLLAMA_API_DISABLED)

    payload = form_data.model_dump()
    model_id = form_data.model

    model_info = await Models.get_model_by_id(model_id)
    if model_info:
        if model_info.base_model_id:
            payload['model'] = model_info.base_model_id

        await check_model_access(user, model_info)
    else:
        await check_model_access(user, None)

    url, url_idx = await get_ollama_url(request, payload['model'], url_idx, user)
    api_config = (await Config.get('ollama.api_configs', {})).get(
        str(url_idx),
        (await Config.get('ollama.api_configs', {})).get(url, {}),  # Legacy support
    )

    prefix_id = api_config.get('prefix_id', None)
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    return await send_request(
        f'{url}/v1/responses',
        payload=json.dumps(payload),
        key=get_api_key(url_idx, url, (await Config.get('ollama.api_configs', {}))),
        user=user,
        stream=payload.get('stream', False),
        content_type='text/event-stream' if payload.get('stream', False) else None,
        api_config=api_config,
        request=request,
    )


@router.get('/v1/models')
@router.get('/v1/models/{url_idx}')
async def get_openai_models(
    request: Request,
    url_idx: int | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """List models in the OpenAI-compatible format."""
    if url_idx is None:
        model_list = await get_all_models(request, user=user)
        raw_models = model_list['models']
    else:
        url = (await Config.get('ollama.base_urls', []))[url_idx]
        model_list = await send_request(f'{url}/api/tags', 'GET')
        raw_models = model_list.get('models', [])

    now_ts = int(time.time())
    models = [{'id': m['model'], 'object': 'model', 'created': now_ts, 'owned_by': 'openai'} for m in raw_models]

    if user.role == 'user' and not BYPASS_MODEL_ACCESS_CONTROL:
        model_ids = [m['id'] for m in models]
        model_infos = {mi.id: mi for mi in await Models.get_models_by_ids(model_ids, db=db)}
        user_group_ids = {g.id for g in await Groups.get_groups_by_member_id(user.id, db=db)}
        accessible_ids = await AccessGrants.get_accessible_resource_ids(
            user_id=user.id,
            resource_type='model',
            resource_ids=list(model_infos.keys()),
            permission='read',
            user_group_ids=user_group_ids,
            db=db,
        )
        models = [
            m for m in models if (mi := model_infos.get(m['id'])) and (user.id == mi.user_id or mi.id in accessible_ids)
        ]

    return {'data': models, 'object': 'list'}


class UrlForm(BaseModel):
    """Form carrying a single URL string."""

    url: str


class UploadBlobForm(BaseModel):
    """Form carrying a filename for blob uploads."""

    filename: str


def parse_huggingface_url(hf_url: str) -> str | None:
    """Extract the filename from a HuggingFace download URL."""
    try:
        return urlparse(hf_url).path.split('/')[-1]
    except (ValueError, IndexError):
        return None


async def download_file_stream(
    ollama_url: str,
    file_url: str,
    file_path: str,
    file_name: str,
    chunk_size: int = 1024 * 1024,
):
    """Stream a model file download from *file_url*, then push the blob to Ollama."""
    current_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    headers = {'Range': f'bytes={current_size}-'} if current_size > 0 else {}

    session = await get_session()
    async with session.get(
        file_url,
        headers=headers,
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
        timeout=aiohttp.ClientTimeout(total=600),
    ) as response:
        total_size = int(response.headers.get('content-length', 0)) + current_size

        with open(file_path, 'ab+') as f:
            async for data in response.content.iter_chunked(chunk_size):
                current_size += len(data)
                f.write(data)

                done = current_size == total_size
                progress = round((current_size / total_size) * 100, 2)
                yield f'data: {{"progress": {progress}, "completed": {current_size}, "total": {total_size}}}\n\n'

            if done:
                f.close()
                hashed = await asyncio.to_thread(calculate_sha256, file_path, chunk_size)

                def _read_blob():
                    with open(file_path, 'rb') as blob_f:
                        return blob_f.read()

                blob_data = await asyncio.to_thread(_read_blob)

                blob_url = f'{ollama_url}/api/blobs/sha256:{hashed}'
                async with session.post(
                    blob_url,
                    data=blob_data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as blob_resp:
                    if blob_resp.ok:
                        os.remove(file_path)
                        yield f'data: {json.dumps({"done": done, "blob": f"sha256:{hashed}", "name": file_name})}\n\n'
                    else:
                        raise RuntimeError('Ollama: Could not create blob, Please try again.')


@router.post('/models/download')
@router.post('/models/download/{url_idx}')
async def download_model(
    request: Request,
    form_data: UrlForm,
    url_idx: int | None = None,
    user=Depends(get_admin_user),
):
    """Download a GGUF model from HuggingFace or GitHub and register it with Ollama."""
    allowed_hosts = ['https://huggingface.co/', 'https://github.com/']
    if not any(form_data.url.startswith(host) for host in allowed_hosts):
        raise HTTPException(
            status_code=400,
            detail='Invalid file_url. Only URLs from allowed hosts are permitted.',
        )

    url = (await Config.get('ollama.base_urls', []))[url_idx if url_idx is not None else 0]
    file_name = parse_huggingface_url(form_data.url)

    if not file_name:
        return None

    file_path = os.path.join(UPLOAD_DIR, file_name)
    return StreamingResponse(
        download_file_stream(url, form_data.url, file_path, file_name),
    )


@router.post('/models/upload')
@router.post('/models/upload/{url_idx}')
async def upload_model(
    request: Request,
    file: UploadFile = File(...),
    url_idx: int | None = None,
    user=Depends(get_admin_user),
):
    """Upload a local model file, push it as a blob, and create the model in Ollama."""
    ollama_url = (await Config.get('ollama.base_urls', []))[url_idx if url_idx is not None else 0]

    filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Stage 1: persist the uploaded file to disk
    chunk_size = 1024 * 1024 * 2  # 2 MiB

    def _persist_upload():
        with open(file_path, 'wb') as out_f:
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)

    await asyncio.to_thread(_persist_upload)

    async def file_process_stream():
        nonlocal ollama_url
        total_size = os.path.getsize(file_path)
        log.info(f'Total Model Size: {total_size}')

        # Stage 2: hash the file and emit SSE progress
        file_hash = await asyncio.to_thread(calculate_sha256, file_path, chunk_size)
        log.info(f'Model Hash: {file_hash}')

        try:
            with open(file_path, 'rb') as f:
                bytes_read = 0
                while chunk := f.read(chunk_size):
                    bytes_read += len(chunk)
                    progress = round(bytes_read / total_size * 100, 2)
                    yield f'data: {json.dumps({"progress": progress, "total": total_size, "completed": bytes_read})}\n\n'

            # Stage 3: push blob to Ollama
            def _read_blob():
                with open(file_path, 'rb') as f:
                    return f.read()

            blob_data = await asyncio.to_thread(_read_blob)

            session = await get_session()
            blob_url = f'{ollama_url}/api/blobs/sha256:{file_hash}'
            async with session.post(
                blob_url,
                data=blob_data,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
            ) as resp:
                if not resp.ok:
                    raise Exception('Ollama: Could not create blob, Please try again.')

            log.info('Uploaded to /api/blobs')
            os.remove(file_path)

            # Stage 4: create the model
            model, _ext = os.path.splitext(filename)
            log.info(f'Created Model: {model}')

            create_payload = {
                'model': model,
                'files': {filename: f'sha256:{file_hash}'},
            }
            log.info(f'Model Payload: {create_payload}')

            async with session.post(
                f'{ollama_url}/api/create',
                headers={'Content-Type': 'application/json'},
                data=json.dumps(create_payload),
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
            ) as create_resp:
                if create_resp.ok:
                    log.info('API SUCCESS!')
                    yield f'data: {json.dumps({"done": True, "blob": f"sha256:{file_hash}", "name": filename, "model_created": model})}\n\n'
                else:
                    resp_text = await create_resp.text()
                    raise Exception(f'Failed to create model in Ollama. {resp_text}')

        except Exception as exc:
            yield f'data: {json.dumps({"error": str(exc)})}\n\n'

    return StreamingResponse(file_process_stream(), media_type='text/event-stream')
