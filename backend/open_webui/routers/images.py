from __future__ import annotations

import asyncio
import base64
import io
import logging
import mimetypes
import re
import uuid
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from urllib.parse import quote, urlparse

import aiofiles
import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from open_webui.config import (
    CACHE_DIR,
    ENABLE_OPENAI_IMAGE_EDIT_NORMALIZATION,
    IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN,
    IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_ALLOW_REDIRECTS, AIOHTTP_CLIENT_SESSION_SSL
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.retrieval.web.utils import assert_identity_encoding, get_ssrf_safe_session, validate_url
from open_webui.routers.files import get_file_content_by_id, upload_file_handler
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_headers_and_cookies
from open_webui.utils.images.comfyui import (
    ComfyUICreateImageForm,
    ComfyUIEditImageForm,
    ComfyUIWorkflow,
    comfyui_create_image,
    comfyui_edit_image,
    comfyui_upload_image,
)
from open_webui.utils.images.connections import (
    DEFAULT_GEMINI_IMAGE_MODEL,
    DEFAULT_OPENAI_IMAGE_MODEL,
    IMAGE_CONNECTIONS_CONFIG_KEY,
    IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY,
    IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY,
    get_image_models,
    get_openai_connection_models,
    normalize_image_connection,
    resolve_image_model,
)
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.session_pool import get_session
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# An image can lie as easily as it can illuminate. Let what
# is generated here be honest about what it shows.
IMAGE_CACHE_DIR = CACHE_DIR / 'image' / 'generations'
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

IMAGE_FILE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/mpo': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}

IMAGE_CONFIG_KEYS = {
    'ENABLE_IMAGE_GENERATION': 'image_generation.enable',
    'ENABLE_IMAGE_PROMPT_GENERATION': 'image_generation.prompt.enable',
    'ENABLE_IMAGE_EDIT': 'images.edit.enable',
    'IMAGE_GENERATION_DEFAULT_MODEL': IMAGE_GENERATION_DEFAULT_MODEL_CONFIG_KEY,
    'IMAGE_EDIT_DEFAULT_MODEL': IMAGE_EDIT_DEFAULT_MODEL_CONFIG_KEY,
    'IMAGE_CONNECTIONS': IMAGE_CONNECTIONS_CONFIG_KEY,
    'USER_PERMISSIONS': 'user.permissions',
}


async def get_config_values(key_map: dict[str, str]) -> dict:
    values = await Config.get_many(*key_map.values())
    return {field: values[storage_key] for field, storage_key in key_map.items() if storage_key in values}


async def get_image_config() -> SimpleNamespace:
    return SimpleNamespace(**await get_config_values(IMAGE_CONFIG_KEYS))


def config_updates(data: dict, key_map: dict[str, str]) -> dict:
    return {key_map[field]: value for field, value in data.items() if field in key_map}


def normalize_openai_edit_image_data_url(data_url: str) -> str:
    if not data_url.startswith('data:') or ',' not in data_url:
        return data_url

    header, encoded = data_url.split(',', 1)
    mime_type = header.split(';')[0].lstrip('data:').lower()
    if mime_type not in {'image/jpeg', 'image/jpg', 'image/mpo'}:
        return data_url

    try:
        image_bytes = base64.b64decode(encoded)
        with Image.open(io.BytesIO(image_bytes)) as image:
            orientation = image.getexif().get(274)
            needs_normalization = (
                mime_type == 'image/mpo'
                or image.format == 'MPO'
                or getattr(image, 'n_frames', 1) > 1
                or orientation not in (None, 1)
                or image.mode not in ('RGB', 'L')
            )

            if not needs_normalization:
                return data_url

            image.seek(0)
            image = ImageOps.exif_transpose(image)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            normalized_image = base64.b64encode(output.getvalue()).decode('utf-8')
            return f'data:image/jpeg;base64,{normalized_image}'
    except Exception as e:
        log.debug('Image edit normalization skipped: %s', e)

    return data_url


def get_image_data_url(data: bytes) -> str:
    """Validate image bytes and encode them with their detected MIME type."""
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in {'PNG', 'JPEG', 'MPO', 'WEBP', 'GIF'}:
            raise ValueError('Image must be PNG, JPEG, WebP, or GIF.')
        if image.width * image.height > 25_000_000:
            raise ValueError('Image must be at most 25 megapixels.')
        mime_type = Image.MIME[image.format]
        image.verify()
    # verify() does not decode pixels for every format.
    with Image.open(io.BytesIO(data)) as image:
        image.load()
    return f'data:{mime_type};base64,{base64.b64encode(data).decode("utf-8")}'


def get_image_file_item(base64_string, param_name='image'):
    header, encoded = base64_string.split(',', 1)
    mime_type = header.split(';')[0].lstrip('data:') or 'image/png'
    image_data = base64.b64decode(encoded)
    extension = IMAGE_FILE_EXTENSIONS.get(mime_type.lower()) or mimetypes.guess_extension(mime_type) or '.png'
    return (
        param_name,
        (
            f'{uuid.uuid4()}{extension}',
            io.BytesIO(image_data),
            mime_type,
        ),
    )


def get_automatic1111_api_auth(api_auth: str | None) -> str:
    if not api_auth:
        return ''
    return f'Basic {base64.b64encode(api_auth.encode("utf-8")).decode("utf-8")}'


async def set_automatic1111_model(connection: dict, model: str) -> None:
    """AUTOMATIC1111 holds one checkpoint instance-wide; switch it when the request needs another."""
    if not model:
        return

    headers = {'authorization': get_automatic1111_api_auth(connection.get('key'))}
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/sdapi/v1/options',
        headers=headers,
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        r.raise_for_status()
        options = await r.json()

    if model != options.get('sd_model_checkpoint'):
        log.info('Switching AUTOMATIC1111 checkpoint to %s', model)
        async with session.post(
            url=f'{connection["url"]}/sdapi/v1/options',
            json={**options, 'sd_model_checkpoint': model},
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()


class ImageConnection(BaseModel):
    id: str | None = None
    name: str = ''
    type: str = 'openai'
    url: str = ''
    key: str = ''
    config: dict = {}

    model_config = ConfigDict(extra='allow')


class ImagesConfig(BaseModel):
    ENABLE_IMAGE_GENERATION: bool
    ENABLE_IMAGE_PROMPT_GENERATION: bool
    ENABLE_IMAGE_EDIT: bool
    IMAGE_GENERATION_DEFAULT_MODEL: str = ''
    IMAGE_EDIT_DEFAULT_MODEL: str = ''
    IMAGE_CONNECTIONS: list[ImageConnection] = []


@router.get('/config', response_model=ImagesConfig)
async def get_config(request: Request, user=Depends(get_admin_user)):
    values = await get_config_values(IMAGE_CONFIG_KEYS)
    return {**values, 'IMAGE_CONNECTIONS': values.get('IMAGE_CONNECTIONS') or []}


@router.post('/config/update')
async def update_config(request: Request, form_data: ImagesConfig, user=Depends(get_admin_user)):
    connections = []
    try:
        for connection in form_data.IMAGE_CONNECTIONS:
            connections.append(normalize_image_connection(connection.model_dump()))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    if len({connection['id'] for connection in connections}) != len(connections):
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('Image connection IDs must be unique'))

    updates = config_updates(form_data.model_dump(exclude={'IMAGE_CONNECTIONS'}), IMAGE_CONFIG_KEYS)
    updates[IMAGE_CONNECTIONS_CONFIG_KEY] = connections
    await Config.upsert(updates)

    values = await get_config_values(IMAGE_CONFIG_KEYS)
    await publish_event(
        request,
        EVENTS.CONFIG_UPDATED,
        actor=user,
        subject_id='images',
        data={
            'image_generation_enabled': values.get('ENABLE_IMAGE_GENERATION'),
            'image_edit_enabled': values.get('ENABLE_IMAGE_EDIT'),
            'image_connections': [
                {'id': connection['id'], 'name': connection['name'], 'type': connection['type']}
                for connection in connections
            ],
        },
    )
    return {**values, 'IMAGE_CONNECTIONS': connections}


async def get_gemini_connection_models(connection: dict) -> list[dict]:
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/models',
        headers={'x-goog-api-key': connection.get('key', '')},
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        await raise_for_provider_status(r)
        res = await r.json(content_type=None)

    models = []
    for model in res.get('models') or []:
        model_id = str(model.get('name') or '').removeprefix('models/')
        if not model_id:
            continue
        methods = model.get('supportedGenerationMethods') or []
        models.append(
            {
                'id': model_id,
                'name': model.get('displayName') or model_id,
                'image': 'predict' in methods or 'image' in model_id,
            }
        )
    return models or [{'id': DEFAULT_GEMINI_IMAGE_MODEL, 'name': DEFAULT_GEMINI_IMAGE_MODEL, 'image': True}]


async def get_comfyui_connection_models(connection: dict) -> list[dict]:
    config = connection.get('config') or {}
    headers = {'Authorization': f'Bearer {connection["key"]}'} if connection.get('key') else {}
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/object_info', headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL
    ) as r:
        await raise_for_provider_status(r)
        info = await r.json(content_type=None)

    def options(class_type: str, key: str | None = None) -> list[dict]:
        required = ((info.get(class_type) or {}).get('input') or {}).get('required') or {}
        key = key or next((name for name in required if '_name' in name), None)
        values = (required.get(key) or [[]])[0] if key else []
        return [{'id': value, 'name': value} for value in values if isinstance(value, str)]

    workflow_json = config.get('workflow') or config.get('edit_workflow')
    nodes = config.get('nodes') if config.get('workflow') else config.get('edit_nodes')
    model_node_id = next(
        (node['node_ids'][0] for node in nodes or [] if node.get('type') == 'model' and node.get('node_ids')),
        None,
    )
    if workflow_json and model_node_id:
        workflow = JSONCodec.loads(workflow_json)
        class_type = (workflow.get(model_node_id) or {}).get('class_type')
        if class_type:
            return options(class_type)
    return options('CheckpointLoaderSimple', 'ckpt_name')


async def get_automatic1111_connection_models(connection: dict) -> list[dict]:
    session = await get_session()
    async with session.get(
        url=f'{connection["url"]}/sdapi/v1/sd-models',
        headers={'authorization': get_automatic1111_api_auth(connection.get('key'))},
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        await raise_for_provider_status(r)
        models = await r.json(content_type=None)
    return [{'id': model['title'], 'name': model['model_name']} for model in models]


@router.post('/connections/verify')
async def verify_image_connection(request: Request, form_data: ImageConnection, user=Depends(get_admin_user)):
    """Reach a connection before saving it and list the models it serves."""
    try:
        connection = normalize_image_connection(form_data.model_dump())
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    if not connection['url']:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)

    try:
        if connection['type'] == 'openai':
            return await get_openai_connection_models(request, connection, user)
        if connection['type'] == 'gemini':
            return await get_gemini_connection_models(connection)
        if connection['type'] == 'comfyui':
            return await get_comfyui_connection_models(connection)
        return await get_automatic1111_connection_models(connection)
    except Exception as e:
        log.error(
            f'Failed to verify image connection {connection["url"]}: {str(e) or type(e).__name__}',
            exc_info=not isinstance(e, (aiohttp.ClientConnectionError, aiohttp.ClientResponseError, TimeoutError)),
        )
        error = e.message if isinstance(e, aiohttp.ClientResponseError) else e
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT(error, 'Failed to connect to the image generation engine'),
        )


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    """Image models this user can pick from, with what each can do."""
    image_config = await get_image_config()
    if not (image_config.ENABLE_IMAGE_GENERATION or image_config.ENABLE_IMAGE_EDIT):
        return []

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.image_generation', image_config.USER_PERMISSIONS
    ):
        return []

    return [
        {key: value for key, value in model.items() if key != 'connection'}
        for model in await get_image_models(request, user)
    ]


@router.get('/connections/models')
async def get_connection_models(request: Request, user=Depends(get_admin_user)):
    """Every model the enabled connections offer, whoever may use them, for choosing the default models."""
    return [
        {key: value for key, value in model.items() if key != 'connection'}
        for model in await get_image_models(request, user, bypass_access=True)
    ]


class CreateImageForm(BaseModel):
    model: str | None = None
    prompt: str
    size: str | None = None
    n: int = 1
    steps: int | None = None
    negative_prompt: str | None = None


GenerateImageForm = CreateImageForm  # Alias for backward compatibility


async def raise_for_provider_status(r: aiohttp.ClientResponse) -> None:
    """Like raise_for_status, but keeps the provider's own error message (e.g. "Invalid size")."""
    if r.ok:
        return

    detail = ''
    try:
        text = await r.text()
        try:
            body = JSONCodec.loads(text)
        except Exception:
            body = None
        error = body.get('error') if isinstance(body, dict) else None
        if isinstance(error, dict):
            detail = error.get('message') or ''
        elif isinstance(error, str):
            detail = error
        elif isinstance(body, dict) and isinstance(body.get('message'), str):
            detail = body['message']
        else:
            detail = text.strip()
    except Exception:
        pass

    message = f'{r.status} {r.reason}'
    if detail:
        message = f'{message}: {detail[:500]}'
    raise aiohttp.ClientResponseError(r.request_info, r.history, status=r.status, message=message, headers=r.headers)


def _is_same_origin(url: str, base_url: str) -> bool:
    """Compare scheme + hostname + port of two URLs.

    Pure string-prefix matching (``startswith``) is vulnerable to
    userinfo injection (``http://host:port@evil.com/``) and suffix
    confusion (``http://host:portevil.com/``).  Parsing both URLs
    and comparing the three origin components eliminates those
    attack vectors.
    """

    def _default_port(scheme: str) -> int:
        return 443 if scheme == 'https' else 80

    parsed = urlparse(url)
    trusted = urlparse(base_url)
    return (
        parsed.scheme == trusted.scheme
        and parsed.hostname == trusted.hostname
        and (parsed.port or _default_port(parsed.scheme)) == (trusted.port or _default_port(trusted.scheme))
    )


async def get_image_data(data: str, headers=None, trusted_base_url: str | None = None):
    try:
        if data.startswith('http://') or data.startswith('https://'):
            # Defense-in-depth: gate before fetch (mirrors load_url_image).
            # For URLs originating from an admin-configured backend (e.g.
            # ComfyUI on a private network), skip SSRF validation only when
            # the URL shares the exact same origin (scheme + host + port)
            # as the admin-configured base.  This avoids both the global
            # ENABLE_LOCAL_WEB_FETCH hammer and a blanket trust flag
            # that would follow arbitrary redirects.
            if trusted_base_url and _is_same_origin(data, trusted_base_url):
                log.debug('Skipping URL validation for trusted backend: %s', data)
                session_context = nullcontext(await get_session())
            else:
                await asyncio.to_thread(validate_url, data)
                session_context = get_ssrf_safe_session()
            async with (
                session_context as session,
                session.get(
                    data,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r,
            ):
                r.raise_for_status()
                content_type = r.headers.get('content-type', '')
                if content_type.split('/')[0] == 'image':
                    return await r.read(), content_type
                else:
                    log.error('Url does not point to an image.')
                    return None, None
        else:
            if ',' in data:
                header, encoded = data.split(',', 1)
                mime_type = header.split(';')[0].lstrip('data:')
                img_data = base64.b64decode(encoded)
            else:
                img_data = base64.b64decode(data)
                with Image.open(io.BytesIO(img_data)) as image:
                    mime_type = Image.MIME.get(image.format, 'image/png')
            return img_data, mime_type
    except Exception as e:
        log.exception(f'Error loading image data: {e}')
        return None, None


async def upload_image(request, image_data, content_type, metadata, user, db=None, name='generated-image'):
    if image_data is None or content_type is None:
        raise ValueError('Failed to retrieve image data from the generation backend')
    image_format = IMAGE_FILE_EXTENSIONS.get(content_type.lower()) or mimetypes.guess_extension(content_type) or '.png'
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f'{name}{image_format}',  # will be converted to a unique ID on upload_file
        headers={
            'content-type': content_type,
        },
    )
    file_item = await upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )

    if file_item and file_item.id:
        # If chat_id and message_id are provided in metadata, link the file to the chat message
        chat_id = metadata.get('chat_id')
        message_id = metadata.get('message_id')

        if chat_id and message_id:
            await Chats.insert_chat_files(
                chat_id=chat_id,
                message_id=message_id,
                file_ids=[file_item.id],
                user_id=user.id,
                db=db,
            )

    url = request.app.url_path_for('get_file_content_by_id', id=file_item.id)
    return file_item, {
        'id': file_item.id,
        'url': url,
        'name': (file_item.meta or {}).get('name') or file_item.filename,
        'content_type': (file_item.meta or {}).get('content_type'),
    }


@router.post('/generations')
async def generate_images(request: Request, form_data: CreateImageForm, user=Depends(get_verified_user)):
    image_config = await get_image_config()
    if not image_config.ENABLE_IMAGE_GENERATION:
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.image_generation', image_config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await image_generations(request, form_data, user=user, strict=True)
    await publish_event(
        request,
        EVENTS.IMAGE_GENERATED,
        actor=user,
        subject_id=None,
        subject_type='image',
        data={
            'model': form_data.model,
            'size': form_data.size,
            'n': form_data.n,
            'prompt_preview': form_data.prompt[:300],
        },
    )
    return result


async def image_generations(
    request: Request,
    form_data: CreateImageForm,
    metadata: dict | None = None,
    user=None,
    strict: bool = False,
):
    connection, model = await resolve_image_model(request, user, 'image_generation', form_data.model, strict=strict)
    connection_config = connection.get('config') or {}
    connection_size = connection_config.get('size') or ''
    connection_steps = connection_config.get('steps')

    # An 'auto' size has no width and height, so engines that need them fall back to 512x512.
    size = '512x512'
    if 'x' in connection_size:
        size = connection_size

    if form_data.size and 'x' in form_data.size:
        size = form_data.size

    width, height = tuple(map(int, size.split('x')))

    metadata = metadata or {}

    try:
        if connection['type'] == 'openai':
            model = model or DEFAULT_OPENAI_IMAGE_MODEL
            headers, cookies = await get_headers_and_cookies(
                request, connection['url'], connection['key'], connection['config'], metadata, user=user
            )

            url = f'{connection["url"]}/images/generations'
            openai_size = form_data.size or connection_size
            # 512x512 is the stock IMAGE_SIZE, left over from DALL-E. GPT image models reject it,
            # so let them pick their own size unless the request asked for one.
            if (
                not form_data.size
                and openai_size == '512x512'
                and re.match(IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN, model)
            ):
                openai_size = 'auto'
            if connection_config.get('api_version'):
                url = f'{url}?api-version={connection_config["api_version"]}'

            data = {
                'model': model,
                'prompt': form_data.prompt,
                'n': form_data.n,
                **({'size': openai_size} if openai_size else {}),
                **(
                    {}
                    if re.match(
                        IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
                        model,
                    )
                    else {'response_format': 'b64_json'}
                ),
                **(connection_config.get('params') or {}),
            }

            session = await get_session()
            async with session.post(
                url=url,
                json=data,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                await raise_for_provider_status(r)
                res = await r.json(content_type=None)

            images = []

            for image in res['data']:
                if image_url := image.get('url', None):
                    image_data, content_type = await get_image_data(
                        image_url,
                        {k: v for k, v in headers.items() if k != 'Content-Type'}
                        if _is_same_origin(image_url, connection['url'])
                        else None,
                    )
                else:
                    image_data, content_type = await get_image_data(image['b64_json'])

                _, image_file = await upload_image(request, image_data, content_type, {**data, **metadata}, user)
                images.append(image_file)
            return images

        elif connection['type'] == 'gemini':
            model = model or DEFAULT_GEMINI_IMAGE_MODEL
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': connection['key'],
            }

            data = {}
            endpoint_method = connection_config.get('endpoint_method') or ''

            if endpoint_method in ('', 'predict'):
                model = f'{model}:predict'
                data = {
                    'instances': {'prompt': form_data.prompt},
                    'parameters': {
                        'sampleCount': form_data.n,
                        'outputOptions': {'mimeType': 'image/png'},
                    },
                }

            elif endpoint_method == 'generateContent':
                model = f'{model}:generateContent'
                data = {'contents': [{'parts': [{'text': form_data.prompt}]}]}

            session = await get_session()
            async with session.post(
                url=f'{connection["url"]}/models/{model}',
                json=data,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                await raise_for_provider_status(r)
                res = await r.json(content_type=None)

            images = []

            if model.endswith(':predict'):
                for image in res['predictions']:
                    image_data, content_type = await get_image_data(image['bytesBase64Encoded'])
                    _, image_file = await upload_image(request, image_data, content_type, {**data, **metadata}, user)
                    images.append(image_file)
            elif model.endswith(':generateContent'):
                for image in res['candidates']:
                    for part in image['content']['parts']:
                        if part.get('inlineData', {}).get('data'):
                            image_data, content_type = await get_image_data(part['inlineData']['data'])
                            _, image_file = await upload_image(
                                request,
                                image_data,
                                content_type,
                                {**data, **metadata},
                                user,
                            )
                            images.append(image_file)

            return images

        elif connection['type'] == 'comfyui':
            data = {
                'prompt': form_data.prompt,
                'width': width,
                'height': height,
                'n': form_data.n,
            }

            if connection_steps is not None or form_data.steps is not None:
                data['steps'] = form_data.steps if form_data.steps is not None else connection_steps

            if form_data.negative_prompt is not None:
                data['negative_prompt'] = form_data.negative_prompt

            form_data = ComfyUICreateImageForm(
                **{
                    'workflow': ComfyUIWorkflow(
                        **{
                            'workflow': connection_config.get('workflow') or '',
                            'nodes': connection_config.get('nodes') or [],
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_create_image(
                model,
                form_data,
                str(uuid.uuid4()),
                connection['url'],
                connection['key'],
            )
            log.debug('res: %s', res)

            images = []

            for image in res['data']:
                headers = None
                if connection['key']:
                    headers = {'Authorization': f'Bearer {connection["key"]}'}

                image_data, content_type = await get_image_data(
                    image['url'],
                    headers,
                    trusted_base_url=connection['url'],
                )
                _, image_file = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**form_data.model_dump(exclude_none=True), **metadata},
                    user,
                )
                images.append(image_file)
            return images
        elif connection['type'] == 'automatic1111':
            # The checkpoint is shared by everyone on this backend. Only models an admin listed on
            # the connection reach here, so switching to one is what the admin allowed.
            await set_automatic1111_model(connection, model)

            data = {
                'prompt': form_data.prompt,
                'batch_size': form_data.n,
                'width': width,
                'height': height,
            }

            if connection_steps is not None or form_data.steps is not None:
                data['steps'] = form_data.steps if form_data.steps is not None else connection_steps

            if form_data.negative_prompt is not None:
                data['negative_prompt'] = form_data.negative_prompt

            if connection_config.get('params'):
                data = {**data, **connection_config['params']}

            session = await get_session()
            async with session.post(
                url=f'{connection["url"]}/sdapi/v1/txt2img',
                json=data,
                headers={'authorization': get_automatic1111_api_auth(connection['key'])},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                res = await r.json(content_type=None)
            log.debug('res: %s', res)

            images = []

            for image in res['images']:
                image_data, content_type = await get_image_data(image)
                _, image_file = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**data, 'info': res['info'], **metadata},
                    user,
                )
                images.append(image_file)
            return images
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))


async def load_url_image(data: str, user) -> str:
    """An image as a data URL, from a data URL, a web URL (SSRF-checked) or an Open WebUI file."""
    if data.startswith('data:'):
        return data

    if data.startswith('http://') or data.startswith('https://'):
        parsed = urlparse(data)
        # Fetching /api/v1/files/{id}/content over the network would be unauthenticated.
        if parsed.path.startswith('/api/v1/files/') and '/content' in parsed.path:
            return await load_url_image(parsed.path, user)

        # Validate URL to prevent SSRF attacks against local/private networks.
        # allow_redirects=False prevents redirect-based SSRF: validate_url() is
        # called only on the originally-submitted URL; following 3xx redirects
        # without re-validation would let an attacker reach private IPs via a
        # public host that redirects internally (e.g. cloud-metadata exfil).
        await asyncio.to_thread(validate_url, data)
        # SSRF-safe session: re-checks the connect-time IP so a rebinding DNS answer
        # that passed validate_url cannot reach an internal address.
        async with get_ssrf_safe_session() as session:
            async with session.get(
                data,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS,
                headers={'Accept-Encoding': 'identity'},
            ) as r:
                r.raise_for_status()
                assert_identity_encoding(r.headers.getall('Content-Encoding', ()))

                image_data = base64.b64encode(await r.read()).decode('utf-8')
                return f'data:{r.headers["content-type"]};base64,{image_data}'

    else:
        file_id = None
        if data.startswith('/api/v1/files'):
            file_id = data.split('/api/v1/files/')[1].split('/content')[0]
        else:
            file_id = data

        file_response = await get_file_content_by_id(file_id, user)
        if isinstance(file_response, FileResponse):
            file_path = file_response.path

            async with aiofiles.open(file_path, 'rb') as f:
                file_bytes = await f.read()
            image_data = base64.b64encode(file_bytes).decode('utf-8')
            mime_type, _ = mimetypes.guess_type(file_path)

            return f'data:{mime_type};base64,{image_data}'
    return data


class EditImageForm(BaseModel):
    image: str | list[str]  # base64-encoded image(s) or URL(s)
    prompt: str
    model: str | None = None
    size: str | None = None
    n: int | None = None
    negative_prompt: str | None = None
    background: str | None = None


@router.post('/edit')
async def edit_images(request: Request, form_data: EditImageForm, user=Depends(get_verified_user)):
    # Authorize the direct route like /generations and the edit_image tool: enforce the
    # global image-edit switch and the per-user image-generation permission. The internal
    # callers (edit_image tool, chat middleware) gate themselves and call image_edits()
    # directly, so they are unaffected by this wrapper.
    image_config = await get_image_config()
    if not image_config.ENABLE_IMAGE_EDIT:
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.image_generation', image_config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await image_edits(request, form_data, user=user, strict=True)
    await publish_event(
        request,
        EVENTS.IMAGE_EDITED,
        actor=user,
        subject_id=None,
        subject_type='image',
        data={
            'model': form_data.model,
            'size': form_data.size,
            'n': form_data.n,
            'prompt_preview': form_data.prompt[:300],
        },
    )
    return result


async def image_edits(
    request: Request,
    form_data: EditImageForm,
    metadata: dict | None = None,
    user=Depends(get_verified_user),
    strict: bool = False,
):
    connection, model = await resolve_image_model(request, user, 'image_edit', form_data.model, strict=strict)
    connection_config = connection.get('config') or {}
    connection_size = connection_config.get('edit_size') or ''
    size = None
    width, height = None, None
    metadata = metadata or {}

    if 'x' in connection_size or (form_data.size and 'x' in form_data.size):
        size = form_data.size if form_data.size else connection_size
        width, height = tuple(map(int, size.split('x')))

    try:
        # Load image(s) from URL(s) if necessary
        if isinstance(form_data.image, str):
            form_data.image = await load_url_image(form_data.image, user)
        elif isinstance(form_data.image, list):
            # Load all images in parallel for better performance
            form_data.image = list(await asyncio.gather(*[load_url_image(img, user) for img in form_data.image]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error loading image'),
        )

    try:
        if connection['type'] == 'openai':
            model = model or DEFAULT_OPENAI_IMAGE_MODEL
            headers, cookies = await get_headers_and_cookies(
                request, connection['url'], connection['key'], connection['config'], metadata, user=user
            )
            # The edit is a multipart upload; aiohttp sets its own content type and boundary.
            headers.pop('Content-Type', None)

            data = {
                'model': model,
                'prompt': form_data.prompt,
                **({'n': form_data.n} if form_data.n else {}),
                **({'size': size} if size else {}),
                **({'background': form_data.background} if form_data.background else {}),
                **(
                    {}
                    if re.match(
                        IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
                        model,
                    )
                    else {'response_format': 'b64_json'}
                ),
            }

            files = []
            if isinstance(form_data.image, str):
                image = form_data.image
                if ENABLE_OPENAI_IMAGE_EDIT_NORMALIZATION:
                    image = normalize_openai_edit_image_data_url(image)
                files = [get_image_file_item(image)]
            elif isinstance(form_data.image, list):
                for img in form_data.image:
                    if ENABLE_OPENAI_IMAGE_EDIT_NORMALIZATION:
                        img = normalize_openai_edit_image_data_url(img)
                    files.append(get_image_file_item(img, 'image[]'))

            url_search_params = ''
            if connection_config.get('api_version'):
                url_search_params += f'?api-version={connection_config["api_version"]}'

            # Build multipart form data for aiohttp
            form = aiohttp.FormData()
            for key, value in data.items():
                if isinstance(value, dict):
                    form.add_field(key, JSONCodec.dumps(value))
                else:
                    form.add_field(key, str(value))
            for param_name, (filename, file_obj, content_type_val) in files:
                form.add_field(
                    param_name,
                    file_obj,
                    filename=filename,
                    content_type=content_type_val,
                )

            session = await get_session()
            async with session.post(
                url=f'{connection["url"]}/images/edits{url_search_params}',
                headers=headers,
                cookies=cookies,
                data=form,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                await raise_for_provider_status(r)
                res = await r.json(content_type=None)

            images = []
            for image in res['data']:
                if image_url := image.get('url', None):
                    image_data, content_type = await get_image_data(
                        image_url,
                        {k: v for k, v in headers.items() if k != 'Content-Type'}
                        if _is_same_origin(image_url, connection['url'])
                        else None,
                    )
                else:
                    image_data, content_type = await get_image_data(image['b64_json'])

                _, image_file = await upload_image(request, image_data, content_type, {**data, **metadata}, user)
                images.append(image_file)
            return images

        elif connection['type'] == 'gemini':
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': connection['key'],
            }

            model = f'{model}:generateContent'
            data = {'contents': [{'parts': [{'text': form_data.prompt}]}]}

            if isinstance(form_data.image, str):
                data['contents'][0]['parts'].append(
                    {
                        'inline_data': {
                            'mime_type': 'image/png',
                            'data': form_data.image.split(',', 1)[1],
                        }
                    }
                )
            elif isinstance(form_data.image, list):
                data['contents'][0]['parts'].extend(
                    [
                        {
                            'inline_data': {
                                'mime_type': 'image/png',
                                'data': image.split(',', 1)[1],
                            }
                        }
                        for image in form_data.image
                    ]
                )

            session = await get_session()
            async with session.post(
                url=f'{connection["url"]}/models/{model}',
                json=data,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                await raise_for_provider_status(r)
                res = await r.json(content_type=None)

            images = []
            for image in res['candidates']:
                for part in image['content']['parts']:
                    if part.get('inlineData', {}).get('data'):
                        image_data, content_type = await get_image_data(part['inlineData']['data'])
                        _, image_file = await upload_image(
                            request,
                            image_data,
                            content_type,
                            {**data, **metadata},
                            user,
                        )
                        images.append(image_file)

            return images

        elif connection['type'] == 'comfyui':
            try:
                files = []
                if isinstance(form_data.image, str):
                    files = [get_image_file_item(form_data.image)]
                elif isinstance(form_data.image, list):
                    for img in form_data.image:
                        files.append(get_image_file_item(img))

                # Upload images to ComfyUI and get their names
                comfyui_images = []
                for file_item in files:
                    res = await comfyui_upload_image(
                        file_item,
                        connection['url'],
                        connection['key'],
                    )
                    comfyui_images.append(res.get('name', file_item[1][0]))
            except Exception as e:
                log.debug('Error uploading images to ComfyUI: %s', e)
                raise Exception('Failed to upload images to ComfyUI.')

            data = {
                'image': comfyui_images,
                'prompt': form_data.prompt,
                **({'width': width} if width is not None else {}),
                **({'height': height} if height is not None else {}),
                **({'n': form_data.n} if form_data.n else {}),
            }

            form_data = ComfyUIEditImageForm(
                **{
                    'workflow': ComfyUIWorkflow(
                        **{
                            'workflow': connection_config.get('edit_workflow') or '',
                            'nodes': connection_config.get('edit_nodes') or [],
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_edit_image(
                model,
                form_data,
                str(uuid.uuid4()),
                connection['url'],
                connection['key'],
            )
            log.debug('res: %s', res)

            image_urls = set()
            for image in res['data']:
                image_urls.add(image['url'])
            image_urls = list(image_urls)

            # Prioritize output type URLs if available
            output_type_urls = [url for url in image_urls if 'type=output' in url]
            if output_type_urls:
                image_urls = output_type_urls

            log.debug('Image URLs: %s', image_urls)
            images = []

            for image_url in image_urls:
                headers = None
                if connection['key']:
                    headers = {'Authorization': f'Bearer {connection["key"]}'}

                image_data, content_type = await get_image_data(
                    image_url,
                    headers,
                    trusted_base_url=connection['url'],
                )
                _, image_file = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**form_data.model_dump(exclude_none=True), **metadata},
                    user,
                )
                images.append(image_file)

            return images
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message

        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))
