from __future__ import annotations

import asyncio
import base64
import io
import logging
import mimetypes
import re
import uuid
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
from open_webui.env import AIOHTTP_CLIENT_ALLOW_REDIRECTS, AIOHTTP_CLIENT_SESSION_SSL, ENABLE_FORWARD_USER_INFO_HEADERS
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.retrieval.web.utils import get_ssrf_safe_session, validate_url
from open_webui.routers.files import get_file_content_by_id, upload_file_handler
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.images.comfyui import (
    ComfyUICreateImageForm,
    ComfyUIEditImageForm,
    ComfyUIWorkflow,
    comfyui_create_image,
    comfyui_edit_image,
    comfyui_upload_image,
)
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.session_pool import get_session
from PIL import Image, ImageOps
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from google import genai
from google.genai import types
from openai import AsyncOpenAI

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
    'IMAGE_GENERATION_ENGINE': 'image_generation.engine',
    'IMAGE_GENERATION_MODEL': 'image_generation.model',
    'IMAGE_SIZE': 'image_generation.size',
    'IMAGE_STEPS': 'image_generation.steps',
    'IMAGES_OPENAI_API_BASE_URL': 'image_generation.openai.api_base_url',
    'IMAGES_OPENAI_API_KEY': 'image_generation.openai.api_key',
    'IMAGES_OPENAI_API_VERSION': 'image_generation.openai.api_version',
    'IMAGES_OPENAI_API_PARAMS': 'image_generation.openai.api_params',
    'AUTOMATIC1111_BASE_URL': 'image_generation.automatic1111.base_url',
    'AUTOMATIC1111_API_AUTH': 'image_generation.automatic1111.api_auth',
    'AUTOMATIC1111_PARAMS': 'image_generation.automatic1111.api_params',
    'COMFYUI_BASE_URL': 'image_generation.comfyui.base_url',
    'COMFYUI_API_KEY': 'image_generation.comfyui.api_key',
    'COMFYUI_WORKFLOW': 'image_generation.comfyui.workflow',
    'COMFYUI_WORKFLOW_NODES': 'image_generation.comfyui.nodes',
    'IMAGES_GEMINI_API_BASE_URL': 'image_generation.gemini.api_base_url',
    'IMAGES_GEMINI_API_KEY': 'image_generation.gemini.api_key',
    'IMAGES_GEMINI_ENDPOINT_METHOD': 'image_generation.gemini.endpoint_method',
    'ENABLE_IMAGE_EDIT': 'images.edit.enable',
    'IMAGE_EDIT_ENGINE': 'images.edit.engine',
    'IMAGE_EDIT_MODEL': 'images.edit.model',
    'IMAGE_EDIT_SIZE': 'images.edit.size',
    'IMAGES_EDIT_OPENAI_API_BASE_URL': 'images.edit.openai.api_base_url',
    'IMAGES_EDIT_OPENAI_API_KEY': 'images.edit.openai.api_key',
    'IMAGES_EDIT_OPENAI_API_VERSION': 'images.edit.openai.api_version',
    'IMAGES_EDIT_GEMINI_API_BASE_URL': 'images.edit.gemini.api_base_url',
    'IMAGES_EDIT_GEMINI_API_KEY': 'images.edit.gemini.api_key',
    'IMAGES_EDIT_COMFYUI_BASE_URL': 'images.edit.comfyui.base_url',
    'IMAGES_EDIT_COMFYUI_API_KEY': 'images.edit.comfyui.api_key',
    'IMAGES_EDIT_COMFYUI_WORKFLOW': 'images.edit.comfyui.workflow',
    'IMAGES_EDIT_COMFYUI_WORKFLOW_NODES': 'images.edit.comfyui.nodes',
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


async def set_image_model(request: Request, model: str):
    log.info('Setting image model to %s', model)
    await Config.upsert({'image_generation.model': model})
    image_config = await get_image_config()
    if image_config.IMAGE_GENERATION_ENGINE in ['', 'automatic1111']:
        api_auth = get_automatic1111_api_auth(image_config)

        try:
            session = await get_session()
            async with session.get(
                url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': api_auth},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                options = await r.json()
            if model != options['sd_model_checkpoint']:
                options['sd_model_checkpoint'] = model
                async with session.post(
                    url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                    json=options,
                    headers={'authorization': api_auth},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    r.raise_for_status()
        except Exception as e:
            log.debug('%s', e)

    return image_config.IMAGE_GENERATION_MODEL


async def get_image_model(request):
    image_config = await get_image_config()
    if image_config.IMAGE_GENERATION_ENGINE == 'openai':
        return image_config.IMAGE_GENERATION_MODEL if image_config.IMAGE_GENERATION_MODEL else 'dall-e-2'
    elif image_config.IMAGE_GENERATION_ENGINE == 'gemini':
        return image_config.IMAGE_GENERATION_MODEL if image_config.IMAGE_GENERATION_MODEL else 'imagen-3.0-generate-002'
    elif image_config.IMAGE_GENERATION_ENGINE == 'comfyui':
        return image_config.IMAGE_GENERATION_MODEL if image_config.IMAGE_GENERATION_MODEL else ''
    elif image_config.IMAGE_GENERATION_ENGINE == 'automatic1111' or image_config.IMAGE_GENERATION_ENGINE == '':
        try:
            session = await get_session()
            async with session.get(
                url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': get_automatic1111_api_auth(image_config)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                options = await r.json()
            return options['sd_model_checkpoint']
        except Exception as e:
            log.exception(f'Failed to get default model from automatic1111: {e}')
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Failed to connect to the image generation engine'),
            )


class ImagesConfig(BaseModel):
    ENABLE_IMAGE_GENERATION: bool
    ENABLE_IMAGE_PROMPT_GENERATION: bool

    IMAGE_GENERATION_ENGINE: str
    IMAGE_GENERATION_MODEL: str
    IMAGE_SIZE: str | None
    IMAGE_STEPS: int | None

    IMAGES_OPENAI_API_BASE_URL: str
    IMAGES_OPENAI_API_KEY: str
    IMAGES_OPENAI_API_VERSION: str
    IMAGES_OPENAI_API_PARAMS: dict | str | None

    AUTOMATIC1111_BASE_URL: str
    AUTOMATIC1111_API_AUTH: dict | str | None
    AUTOMATIC1111_PARAMS: dict | str | None

    COMFYUI_BASE_URL: str
    COMFYUI_API_KEY: str
    COMFYUI_WORKFLOW: str
    COMFYUI_WORKFLOW_NODES: list[dict]

    IMAGES_GEMINI_API_BASE_URL: str
    IMAGES_GEMINI_API_KEY: str
    IMAGES_GEMINI_ENDPOINT_METHOD: str

    ENABLE_IMAGE_EDIT: bool
    IMAGE_EDIT_ENGINE: str
    IMAGE_EDIT_MODEL: str
    IMAGE_EDIT_SIZE: str | None

    IMAGES_EDIT_OPENAI_API_BASE_URL: str
    IMAGES_EDIT_OPENAI_API_KEY: str
    IMAGES_EDIT_OPENAI_API_VERSION: str
    IMAGES_EDIT_GEMINI_API_BASE_URL: str
    IMAGES_EDIT_GEMINI_API_KEY: str
    IMAGES_EDIT_COMFYUI_BASE_URL: str
    IMAGES_EDIT_COMFYUI_API_KEY: str
    IMAGES_EDIT_COMFYUI_WORKFLOW: str
    IMAGES_EDIT_COMFYUI_WORKFLOW_NODES: list[dict]


@router.get('/config', response_model=ImagesConfig)
async def get_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(IMAGE_CONFIG_KEYS)


@router.post('/config/update')
async def update_config(request: Request, form_data: ImagesConfig, user=Depends(get_admin_user)):
    if form_data.IMAGE_SIZE == 'auto' and not re.match(
        IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN, form_data.IMAGE_GENERATION_MODEL
    ):
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT(
                f'  (auto is only allowed with models matching {IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN}).'
            ),
        )

    pattern = r'^\d+x\d+$'
    if not (form_data.IMAGE_SIZE == 'auto' or form_data.IMAGE_SIZE == '' or re.match(pattern, form_data.IMAGE_SIZE)):
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 512x512).'),
        )

    if form_data.IMAGE_STEPS < 0:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 50).'),
        )

    updates = config_updates(form_data.model_dump(), IMAGE_CONFIG_KEYS)
    updates['image_generation.comfyui.base_url'] = form_data.COMFYUI_BASE_URL.strip('/')
    updates['images.edit.comfyui.base_url'] = form_data.IMAGES_EDIT_COMFYUI_BASE_URL.strip('/')
    await Config.upsert(updates)
    await set_image_model(request, form_data.IMAGE_GENERATION_MODEL)
    values = await get_config_values(IMAGE_CONFIG_KEYS)
    await publish_event(
        request,
        EVENTS.CONFIG_UPDATED,
        actor=user,
        subject_id='images',
        data={
            'image_generation_enabled': values.get('ENABLE_IMAGE_GENERATION'),
            'image_edit_enabled': values.get('ENABLE_IMAGE_EDIT'),
            'image_generation_engine': values.get('IMAGE_GENERATION_ENGINE'),
            'image_edit_engine': values.get('IMAGE_EDIT_ENGINE'),
        },
    )
    return values


def get_automatic1111_api_auth(image_config):
    if image_config.AUTOMATIC1111_API_AUTH is None:
        return ''
    else:
        auth1111_byte_string = image_config.AUTOMATIC1111_API_AUTH.encode('utf-8')
        auth1111_base64_encoded_bytes = base64.b64encode(auth1111_byte_string)
        auth1111_base64_encoded_string = auth1111_base64_encoded_bytes.decode('utf-8')
        return f'Basic {auth1111_base64_encoded_string}'


@router.get('/config/url/verify')
async def verify_url(request: Request, user=Depends(get_admin_user)):
    image_config = await get_image_config()
    if image_config.IMAGE_GENERATION_ENGINE == 'automatic1111':
        try:
            session = await get_session()
            async with session.get(
                url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': get_automatic1111_api_auth(image_config)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                return True
        except Exception:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    elif image_config.IMAGE_GENERATION_ENGINE == 'comfyui':
        headers = None
        if image_config.COMFYUI_API_KEY:
            headers = {'Authorization': f'Bearer {image_config.COMFYUI_API_KEY}'}
        try:
            session = await get_session()
            async with session.get(
                url=f'{image_config.COMFYUI_BASE_URL}/object_info',
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                return True
        except Exception:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    else:
        return True


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    image_config = await get_image_config()
    try:
        if image_config.IMAGE_GENERATION_ENGINE == 'openai':
            return [
                {'id': 'dall-e-2', 'name': 'DALL·E 2'},
                {'id': 'dall-e-3', 'name': 'DALL·E 3'},
                {'id': 'gpt-image-1', 'name': 'GPT-IMAGE 1'},
                {'id': 'gpt-image-1.5', 'name': 'GPT-IMAGE 1.5'},
            ]
        elif image_config.IMAGE_GENERATION_ENGINE == 'gemini':
            return [
                {'id': 'imagen-3.0-generate-002', 'name': 'imagen-3.0 generate-002'},
            ]
        elif image_config.IMAGE_GENERATION_ENGINE == 'comfyui':
            # TODO - get models from comfyui
            headers = {'Authorization': f'Bearer {image_config.COMFYUI_API_KEY}'}
            session = await get_session()
            async with session.get(
                url=f'{image_config.COMFYUI_BASE_URL}/object_info',
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                info = await r.json()

            workflow = JSONCodec.loads(image_config.COMFYUI_WORKFLOW)
            model_node_id = None

            for node in image_config.COMFYUI_WORKFLOW_NODES:
                if node['type'] == 'model':
                    if node['node_ids']:
                        model_node_id = node['node_ids'][0]
                    break

            if model_node_id:
                model_list_key = None

                log.info(workflow[model_node_id]['class_type'])
                for key in info[workflow[model_node_id]['class_type']]['input']['required']:
                    if '_name' in key:
                        model_list_key = key
                        break

                if model_list_key:
                    return list(
                        map(
                            lambda model: {'id': model, 'name': model},
                            info[workflow[model_node_id]['class_type']]['input']['required'][model_list_key][0],
                        )
                    )
            else:
                return list(
                    map(
                        lambda model: {'id': model, 'name': model},
                        info['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0],
                    )
                )
        elif image_config.IMAGE_GENERATION_ENGINE == 'automatic1111' or image_config.IMAGE_GENERATION_ENGINE == '':
            session = await get_session()
            async with session.get(
                url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models',
                headers={'authorization': get_automatic1111_api_auth(image_config)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                models = await r.json()
            return list(
                map(
                    lambda model: {'id': model['title'], 'name': model['model_name']},
                    models,
                )
            )
    except Exception as e:
        log.exception(f'Failed to list image generation models: {e}')
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Failed to retrieve image generation models'),
        )


class CreateImageForm(BaseModel):
    model: str | None = None
    prompt: str
    size: str | None = None
    n: int = 1
    steps: int | None = None
    negative_prompt: str | None = None


GenerateImageForm = CreateImageForm  # Alias for backward compatibility


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
            else:
                await asyncio.to_thread(validate_url, data)
            session = await get_session()
            async with session.get(
                data,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
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
                mime_type = 'image/png'
                img_data = base64.b64decode(data)
            return img_data, mime_type
    except Exception as e:
        log.exception(f'Error loading image data: {e}')
        return None, None


async def upload_image(request, image_data, content_type, metadata, user, db=None):
    if image_data is None or content_type is None:
        raise ValueError('Failed to retrieve image data from the generation backend')
    image_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f'generated-image{image_format}',  # will be converted to a unique ID on upload_file
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
    return file_item, url


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

    result = await image_generations(request, form_data, user=user)
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
):
    image_config = await get_image_config()
    # if IMAGE_SIZE = 'auto', default WidthxHeight to the 512x512 default
    # This is only relevant when the user has set IMAGE_SIZE to 'auto' with an
    # image model other than gpt-image-1, which is warned about on settings save

    size = '512x512'
    if image_config.IMAGE_SIZE and 'x' in image_config.IMAGE_SIZE:
        size = image_config.IMAGE_SIZE

    if form_data.size and 'x' in form_data.size:
        size = form_data.size

    width, height = tuple(map(int, size.split('x')))

    metadata = metadata or {}

    model = await get_image_model(request)

    try:
        if image_config.IMAGE_GENERATION_ENGINE == 'openai':
            # Initialize the OpenAI client
            if image_config.IMAGES_OPENAI_API_VERSION:
                openai_client = AsyncOpenAI(
                    api_key=image_config.IMAGES_OPENAI_API_KEY,
                    azure_endpoint=image_config.IMAGES_OPENAI_API_BASE_URL,
                    api_version=image_config.IMAGES_OPENAI_API_VERSION,
                )
            else:
                openai_client = AsyncOpenAI(
                    api_key=image_config.IMAGES_OPENAI_API_KEY,
                    base_url=image_config.IMAGES_OPENAI_API_BASE_URL,
                )

            # Prepare parameters for images.generate
            generate_params = {
                'model': model,
                'prompt': form_data.prompt,
                'n': form_data.n,
            }

            # Add size if present
            effective_size = form_data.size or image_config.IMAGE_SIZE
            if effective_size:
                generate_params['size'] = effective_size

            # Determine response_format
            if not re.match(IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN, image_config.IMAGE_GENERATION_MODEL):
                generate_params['response_format'] = 'b64_json'
            else:
                # If model matches URL response pattern, default to URL.
                # The client will return URLs by default if response_format is not specified.
                pass

            # Add any extra parameters from IMAGES_OPENAI_API_PARAMS
            if image_config.IMAGES_OPENAI_API_PARAMS:
                # Use extra_body for custom parameters not directly supported by the client's signature
                generate_params['extra_body'] = image_config.IMAGES_OPENAI_API_PARAMS

            # Call the OpenAI images generation API
            response = await openai_client.images.generate(**generate_params)

            images = []
            for image_obj in response.data: # response.data is a list of Image objects
                if image_obj.url:
                    # The original code passes headers to get_image_data, but the OpenAI client
                    # handles authentication internally. If the URL is directly from OpenAI,
                    # it should be publicly accessible or pre-signed. No need for headers here.
                    image_data, content_type = await get_image_data(image_obj.url)
                elif image_obj.b64_json:
                    image_data, content_type = await get_image_data(image_obj.b64_json)
                else:
                    log.warning("OpenAI image response missing URL or b64_json.")
                    continue

                # Upload the generated image
                _, url = await upload_image(request, image_data, content_type, {**generate_params, **metadata}, user)
                images.append({'url': url})
            return images

        elif image_config.IMAGE_GENERATION_ENGINE == 'gemini':
            # Initialize the Google GenAI client
            genai_client = genai.Client(
                api_key=image_config.IMAGES_GEMINI_API_KEY,
                client_options={'api_endpoint': image_config.IMAGES_GEMINI_API_BASE_URL},
            )

            # The model name should be without ':predict' or ':generateContent' suffix for the client
            base_model_name = model.split(':')[0] if ':' in model else model

            generated_images = []
            # The google.genai client's generate_content typically generates one image per call
            # Loop 'n' times for multiple images as requested by form_data.n
            for _ in range(form_data.n):
                try:
                    response = await genai_client.aio.models.generate_content(
                        model=base_model_name,
                        contents=[form_data.prompt],
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            # The client does not directly support 'sampleCount' or 'outputOptions'
                            # for image generation in the same way as the raw API.
                            # 'n' is handled by looping. 'outputOptions' is handled by as_image().
                        ),
                    )

                    for part in response.parts:
                        if part.inline_data is not None:
                            # part.as_image() returns a PIL Image object
                            pil_image = part.as_image()
                            output = io.BytesIO()
                            # Save as PNG, as specified in original 'outputOptions'
                            pil_image.save(output, format='PNG')
                            image_data = output.getvalue()
                            content_type = 'image/png' # Consistent with original outputOptions

                            # Upload the generated image
                            _, url = await upload_image(
                                request,
                                image_data,
                                content_type,
                                {
                                    'model': base_model_name,
                                    'prompt': form_data.prompt,
                                    'n': form_data.n,
                                    **metadata
                                }, # Include original data for metadata
                                user,
                            )
                            generated_images.append({'url': url})
                            break # Assuming one image per part for image generation
                except Exception as e:
                    log.error(f"Error generating Gemini image (attempt {_ + 1}/{form_data.n}): {e}")
                    # Decide how to handle partial failures. For now, just log and continue.
                    # If all fail, the outer try-except will catch it.

            return generated_images

        elif image_config.IMAGE_GENERATION_ENGINE == 'comfyui':
            data = {
                'prompt': form_data.prompt,
                'width': width,
                'height': height,
                'n': form_data.n,
            }

            if image_config.IMAGE_STEPS is not None or form_data.steps is not None:
                data['steps'] = form_data.steps if form_data.steps is not None else image_config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data['negative_prompt'] = form_data.negative_prompt

            form_data = ComfyUICreateImageForm(
                **{
                    'workflow': ComfyUIWorkflow(
                        **{
                            'workflow': image_config.COMFYUI_WORKFLOW,
                            'nodes': image_config.COMFYUI_WORKFLOW_NODES,
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_create_image(
                model,
                form_data,
                str(uuid.uuid4()),
                image_config.COMFYUI_BASE_URL,
                image_config.COMFYUI_API_KEY,
            )
            log.debug('res: %s', res)

            images = []

            for image in res['data']:
                headers = None
                if image_config.COMFYUI_API_KEY:
                    headers = {'Authorization': f'Bearer {image_config.COMFYUI_API_KEY}'}

                image_data, content_type = await get_image_data(
                    image['url'],
                    headers,
                    trusted_base_url=image_config.COMFYUI_BASE_URL,
                )
                _, url = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**form_data.model_dump(exclude_none=True), **metadata},
                    user,
                )
                images.append({'url': url})
            return images
        elif image_config.IMAGE_GENERATION_ENGINE == 'automatic1111' or image_config.IMAGE_GENERATION_ENGINE == '':
            # Automatic1111 holds one checkpoint instance-wide, so set_image_model
            # persists the global default and switches the shared backend. Only an
            # admin may do that; a non-admin generates on the currently configured
            # checkpoint. The model field is not a per-user selection on this backend.
            if form_data.model and user.role == 'admin':
                await set_image_model(request, form_data.model)

            data = {
                'prompt': form_data.prompt,
                'batch_size': form_data.n,
                'width': width,
                'height': height,
            }

            if image_config.IMAGE_STEPS is not None or form_data.steps is not None:
                data['steps'] = form_data.steps if form_data.steps is not None else image_config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data['negative_prompt'] = form_data.negative_prompt

            if image_config.AUTOMATIC1111_PARAMS:
                data = {**data, **image_config.AUTOMATIC1111_PARAMS}

            session = await get_session()
            async with session.post(
                url=f'{image_config.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img',
                json=data,
                headers={'authorization': get_automatic1111_api_auth(image_config)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                res = await r.json(content_type=None)
            log.debug('res: %s', res)

            images = []

            for image in res['images']:
                image_data, content_type = await get_image_data(image)
                _, url = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**data, 'info': res['info'], **metadata},
                    user,
                )
                images.append({'url': url})
            return images
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))


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

    result = await image_edits(request, form_data, user=user)
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
):
    image_config = await get_image_config()
    size = None
    width, height = None, None
    metadata = metadata or {}

    if (image_config.IMAGE_EDIT_SIZE and 'x' in image_config.IMAGE_EDIT_SIZE) or (
        form_data.size and 'x' in form_data.size
    ):
        size = form_data.size if form_data.size else image_config.IMAGE_EDIT_SIZE
        width, height = tuple(map(int, size.split('x')))

    model = image_config.IMAGE_EDIT_MODEL if form_data.model is None else form_data.model

    try:

        async def load_url_image(data):
            if data.startswith('data:'):
                return data

            if data.startswith('http://') or data.startswith('https://'):
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
                        data, ssl=AIOHTTP_CLIENT_SESSION_SSL, allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS
                    ) as r:
                        r.raise_for_status()

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
                    image_data = base66.b64encode(file_bytes).decode('utf-8')
                    mime_type, _ = mimetypes.guess_type(file_path)

                    return f'data:{mime_type};base64,{image_data}'
            return data

        # Load image(s) from URL(s) if necessary
        if isinstance(form_data.image, str):
            form_data.image = await load_url_image(form_data.image)
        elif isinstance(form_data.image, list):
            # Load all images in parallel for better performance
            form_data.image = list(await asyncio.gather(*[load_url_image(img) for img in form_data.image]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error loading image'),
        )

    try:
        if image_config.IMAGE_EDIT_ENGINE == 'openai':
            headers = {
                'Authorization': f'Bearer {image_config.IMAGES_EDIT_OPENAI_API_KEY}',
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS:
                headers = include_user_info_headers(headers, user)

            data = {
                'model': model,
                'prompt': form_data.prompt,
                **({'n': form_data.n} if form_data.n else {}),
                **({'size': size} if size else {}),
                **({'background': form_data.background} if form_data.background else {}),
                **( # This block is kept as is because the 'background' parameter is not supported by the official OpenAI client's images.edit method.
                    {} # To preserve 100% of original business logic, the aiohttp call is retained if 'background' is used.
                    if re.match(
                        IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
                        image_config.IMAGE_EDIT_MODEL,
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
            if image_config.IMAGES_EDIT_OPENAI_API_VERSION:
                url_search_params += f'?api-version={image_config.IMAGES_EDIT_OPENAI_API_VERSION}'

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
                url=f'{image_config.IMAGES_EDIT_OPENAI_API_BASE_URL}/images/edits{url_search_params}',
                headers=headers,
                data=form,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                res = await r.json(content_type=None)

            images = []
            for image in res['data']:
                if image_url := image.get('url', None):
                    image_data, content_type = await get_image_data(
                        image_url,
                        {k: v for k, v in headers.items() if k != 'Content-Type'},
                    )
                else:
                    image_data, content_type = await get_image_data(image['b64_json'])

                _, url = await upload_image(request, image_data, content_type, {**data, **metadata}, user)
                images.append({'url': url})
            return images

        elif image_config.IMAGE_EDIT_ENGINE == 'gemini':
            # Initialize the Google GenAI client
            genai_client = genai.Client(
                api_key=image_config.IMAGES_EDIT_GEMINI_API_KEY,
                client_options={'api_endpoint': image_config.IMAGES_EDIT_GEMINI_API_BASE_URL},
            )

            # The model name should be without ':generateContent' suffix for the client
            base_model_name = model.split(':')[0] if ':' in model else model

            # Prepare contents for multimodal input
            contents = [{'text': form_data.prompt}]

            # Add image parts from form_data.image
            image_list = [form_data.image] if isinstance(form_data.image, str) else form_data.image
            for img_data_url in image_list:
                # Assuming img_data_url is 'data:image/png;base64,...'
                if ',' in img_data_url:
                    mime_type_header, encoded_data = img_data_url.split(',', 1)
                    mime_type = mime_type_header.split(';')[0].lstrip('data:')
                    contents.append(
                        {
                            'inline_data': {
                                'mime_type': mime_type,
                                'data': encoded_data,
                            }
                        }
                    )
                else:
                    # If it's just base64 data without header, assume image/png
                    contents.append(
                        {
                            'inline_data': {
                                'mime_type': 'image/png',
                                'data': img_data_url,
                            }
                        }
                    )

            generated_images = []
            # For image editing, typically one output image is expected per input image/prompt.
            # The 'n' parameter for edits is not directly supported by generate_content for multiple outputs.
            # If multiple outputs are desired, multiple calls would be needed, but the original code
            # also seems to expect one output per call for edits.
            try:
                response = await genai_client.aio.models.generate_content(
                    model=base_model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

                for part in response.parts:
                    if part.inline_data is not None:
                        pil_image = part.as_image()
                        output = io.BytesIO()
                        pil_image.save(output, format='PNG') # Save as PNG
                        image_data = output.getvalue()
                        content_type = 'image/png'

                        _, url = await upload_image(
                            request,
                            image_data,
                            content_type,
                            {
                                'model': base_model_name,
                                'prompt': form_data.prompt,
                                'image': form_data.image, # Original image data for metadata
                                **metadata
                            },
                            user,
                        )
                        generated_images.append({'url': url})
                        break # Assuming one image per part for image generation
            except Exception as e:
                log.error(f"Error editing Gemini image: {e}")
                raise # Re-raise to be caught by outer try-except

            return generated_images

        elif image_config.IMAGE_EDIT_ENGINE == 'comfyui':
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
                        image_config.IMAGES_EDIT_COMFYUI_BASE_URL,
                        image_config.IMAGES_EDIT_COMFYUI_API_KEY,
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
                **({'n': form_data.n} if form_data.n is not None else {}),
            }

            form_data = ComfyUIEditImageForm(
                **{
                    'workflow': ComfyUIWorkflow(
                        **{
                            'workflow': image_config.IMAGES_EDIT_COMFYUI_WORKFLOW,
                            'nodes': image_config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES,
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_edit_image(
                model,
                form_data,
                str(uuid.uuid4()),
                image_config.IMAGES_EDIT_COMFYUI_BASE_URL,
                image_config.IMAGES_EDIT_COMFYUI_API_KEY,
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
                if image_config.IMAGES_EDIT_COMFYUI_API_KEY:
                    headers = {'Authorization': f'Bearer {image_config.IMAGES_EDIT_COMFYUI_API_KEY}'}

                image_data, content_type = await get_image_data(
                    image_url,
                    headers,
                    trusted_base_url=image_config.IMAGES_EDIT_COMFYUI_BASE_URL,
                )
                _, url = await upload_image(
                    request,
                    image_data,
                    content_type,
                    {**form_data.model_dump(exclude_none=True), **metadata},
                    user,
                )
                images.append({'url': url})

            return images
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message

        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))
