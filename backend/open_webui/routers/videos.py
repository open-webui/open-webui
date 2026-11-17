from __future__ import annotations

import asyncio
import logging
import time

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from open_webui.config import VIDEO_GENERATION_POLL_INTERVAL, VIDEO_GENERATION_TIMEOUT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.events import EVENTS, publish_event
from open_webui.models.config import Config
from open_webui.routers.images import (
    get_image_file_item,
    load_url_image,
    raise_for_provider_status,
    upload_image,
)
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_headers_and_cookies
from open_webui.utils.images.connections import get_openai_connection_models
from open_webui.utils.session_pool import get_session
from open_webui.utils.videos.connections import (
    VIDEO_CONNECTIONS_CONFIG_KEY,
    VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY,
    get_video_models,
    normalize_video_connection,
    resolve_video_model,
)
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)

router = APIRouter()


VIDEO_CONFIG_KEYS = {
    'ENABLE_VIDEO_GENERATION': 'video_generation.enable',
    'VIDEO_GENERATION_DEFAULT_MODEL': VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY,
    'VIDEO_CONNECTIONS': VIDEO_CONNECTIONS_CONFIG_KEY,
}


class VideoConnection(BaseModel):
    id: str | None = None
    name: str = ''
    type: str = 'openai'
    url: str = ''
    key: str = ''
    config: dict = {}

    model_config = ConfigDict(extra='allow')


class VideosConfig(BaseModel):
    ENABLE_VIDEO_GENERATION: bool
    VIDEO_GENERATION_DEFAULT_MODEL: str = ''
    VIDEO_CONNECTIONS: list[VideoConnection] = []


async def get_video_config_values() -> dict:
    values = await Config.get_many(*VIDEO_CONFIG_KEYS.values())
    return {
        'ENABLE_VIDEO_GENERATION': bool(values.get('video_generation.enable')),
        'VIDEO_GENERATION_DEFAULT_MODEL': values.get(VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY) or '',
        'VIDEO_CONNECTIONS': values.get(VIDEO_CONNECTIONS_CONFIG_KEY) or [],
    }


@router.get('/config', response_model=VideosConfig)
async def get_config(request: Request, user=Depends(get_admin_user)):
    return await get_video_config_values()


@router.post('/config/update')
async def update_config(request: Request, form_data: VideosConfig, user=Depends(get_admin_user)):
    connections = []
    try:
        for connection in form_data.VIDEO_CONNECTIONS:
            connections.append(normalize_video_connection(connection.model_dump()))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    if len({connection['id'] for connection in connections}) != len(connections):
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('Video connection IDs must be unique'))

    await Config.upsert(
        {
            'video_generation.enable': form_data.ENABLE_VIDEO_GENERATION,
            VIDEO_GENERATION_DEFAULT_MODEL_CONFIG_KEY: form_data.VIDEO_GENERATION_DEFAULT_MODEL,
            VIDEO_CONNECTIONS_CONFIG_KEY: connections,
        }
    )

    values = await get_video_config_values()
    await publish_event(
        request,
        EVENTS.CONFIG_UPDATED,
        actor=user,
        subject_id='videos',
        data={
            'video_generation_enabled': values['ENABLE_VIDEO_GENERATION'],
            'video_connections': [
                {'id': connection['id'], 'name': connection['name'], 'type': connection['type']}
                for connection in connections
            ],
        },
    )
    return values


@router.post('/connections/verify')
async def verify_video_connection(request: Request, form_data: VideoConnection, user=Depends(get_admin_user)):
    """Reach a connection before saving it and list the models it serves."""
    try:
        connection = normalize_video_connection(form_data.model_dump())
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    if not connection['url']:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)

    try:
        return await get_openai_connection_models(request, connection, user)
    except Exception as e:
        log.error(
            f'Failed to verify video connection {connection["url"]}: {str(e) or type(e).__name__}',
            exc_info=not isinstance(e, (aiohttp.ClientConnectionError, aiohttp.ClientResponseError, TimeoutError)),
        )
        error = e.message if isinstance(e, aiohttp.ClientResponseError) else e
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT(error, 'Failed to connect to the video generation server'),
        )


def public_video_model(model: dict) -> dict:
    return {key: value for key, value in model.items() if key != 'connection'}


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    """Video models this user can pick from."""
    if not await Config.get('video_generation.enable'):
        return []

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.video_generation', await Config.get('user.permissions')
    ):
        return []

    return [public_video_model(model) for model in await get_video_models(request, user)]


@router.get('/connections/models')
async def get_connection_models(request: Request, user=Depends(get_admin_user)):
    """Every model the enabled connections offer, whoever may use them, for choosing the default model."""
    return [public_video_model(model) for model in await get_video_models(request, user, bypass_access=True)]


class CreateVideoForm(BaseModel):
    model: str | None = None
    prompt: str
    seconds: int | None = None
    size: str | None = None
    image: str | None = None  # starting frame: a data URL, a URL or an Open WebUI file


@router.post('/generations')
async def generate_videos(request: Request, form_data: CreateVideoForm, user=Depends(get_verified_user)):
    if not await Config.get('video_generation.enable'):
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.video_generation', await Config.get('user.permissions')
    ):
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await video_generations(request, form_data, user=user, strict=True)
    await publish_event(
        request,
        EVENTS.VIDEO_GENERATED,
        actor=user,
        subject_id=None,
        subject_type='video',
        data={
            'model': form_data.model,
            'size': form_data.size,
            'seconds': form_data.seconds,
            'prompt_preview': form_data.prompt[:300],
        },
    )
    return result


async def video_generations(
    request: Request,
    form_data: CreateVideoForm,
    metadata: dict | None = None,
    user=None,
    strict: bool = False,
    event_emitter=None,
):
    """Start a video job, wait for it while reporting progress, and save the finished video as a file.

    Video models take minutes, so the provider runs each request as a job: create it with
    ``POST /videos``, check ``GET /videos/{id}`` until it is done, then download ``/videos/{id}/content``.
    """
    connection, model = await resolve_video_model(request, user, form_data.model, strict=strict)
    connection_config = connection.get('config') or {}
    seconds = form_data.seconds or connection_config.get('seconds')
    size = form_data.size or connection_config.get('size')
    metadata = metadata or {}

    async def emit_status(description: str):
        if event_emitter:
            await event_emitter({'type': 'status', 'data': {'description': description, 'done': False}})

    try:
        headers, cookies = await get_headers_and_cookies(
            request, connection['url'], connection['key'], connection_config, metadata, user=user
        )
        # The create request is multipart, so the connection's JSON content type does not apply.
        headers.pop('Content-Type', None)

        api_version = connection_config.get('api_version')
        query = f'?api-version={api_version}' if api_version else ''
        base_url = f'{connection["url"]}/videos'

        form = aiohttp.FormData()
        if model:
            form.add_field('model', model)
        form.add_field('prompt', form_data.prompt)
        if seconds:
            form.add_field('seconds', str(seconds))
        if size:
            form.add_field('size', size)
        if form_data.image:
            name, (filename, file, content_type) = get_image_file_item(
                await load_url_image(form_data.image, user), 'input_reference'
            )
            form.add_field(name, file, filename=filename, content_type=content_type)
        for key, value in (connection_config.get('params') or {}).items():
            form.add_field(key, value if isinstance(value, str) else str(value))

        session = await get_session()
        async with session.post(
            url=f'{base_url}{query}', data=form, headers=headers, cookies=cookies, ssl=AIOHTTP_CLIENT_SESSION_SSL
        ) as r:
            await raise_for_provider_status(r)
            job = await r.json(content_type=None)

        await emit_status('Generating video')
        deadline = time.monotonic() + VIDEO_GENERATION_TIMEOUT
        # OpenAI's video API (and LiteLLM's, which follows it) reports queued, in_progress, completed or failed.
        while job.get('status') in ('queued', 'in_progress'):
            if time.monotonic() > deadline:
                raise HTTPException(
                    status_code=400, detail=f'The video was not ready after {VIDEO_GENERATION_TIMEOUT} seconds'
                )

            await asyncio.sleep(VIDEO_GENERATION_POLL_INTERVAL)
            async with session.get(
                url=f'{base_url}/{job["id"]}{query}', headers=headers, cookies=cookies, ssl=AIOHTTP_CLIENT_SESSION_SSL
            ) as r:
                await raise_for_provider_status(r)
                job = await r.json(content_type=None)

            if isinstance(job.get('progress'), (int, float)):
                await emit_status(f'Generating video ({round(job["progress"])}%)')

        if job.get('status') != 'completed':
            error = job.get('error')
            message = error.get('message') if isinstance(error, dict) else error
            raise HTTPException(status_code=400, detail=message or f'The video job {job.get("status")}')

        async with session.get(
            url=f'{base_url}/{job["id"]}/content{query}',
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            await raise_for_provider_status(r)
            video_data = await r.read()
            content_type = r.headers.get('content-type', 'video/mp4').split(';')[0] or 'video/mp4'

        _, video_file = await upload_image(
            request,
            video_data,
            content_type,
            {'model': model, 'prompt': form_data.prompt, 'video_id': job['id'], **metadata},
            user,
            name='generated-video',
        )
        return [video_file]
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Video generation failed: {e}')
        error = e.message if isinstance(e, aiohttp.ClientResponseError) else e
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))
