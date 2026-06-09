import json
import logging
import random
import urllib.parse
from typing import Optional

import aiohttp
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.session_pool import get_session
from pydantic import BaseModel

log = logging.getLogger(__name__)

default_headers = {'User-Agent': 'Mozilla/5.0'}


async def queue_prompt(prompt, client_id, base_url, api_key):
    log.info('queue_prompt')
    p = {'prompt': prompt, 'client_id': client_id}
    log.debug(f'queue_prompt data: {p}')
    try:
        session = await get_session()
        async with session.post(
            f'{base_url}/api/prompt',
            json=p,
            headers={**default_headers, 'Authorization': f'Bearer {api_key}'},
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()
            return await r.json()
    except Exception as e:
        log.exception(f'Error while queuing prompt: {e}')
        raise


async def get_image(filename, subfolder, folder_type, base_url, api_key):
    log.info('get_image')
    data = {'filename': filename, 'subfolder': subfolder, 'type': folder_type}
    url_values = urllib.parse.urlencode(data)
    session = await get_session()
    async with session.get(
        f'{base_url}/view?{url_values}',
        headers={**default_headers, 'Authorization': f'Bearer {api_key}'},
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        r.raise_for_status()
        return await r.read()


def get_image_url(filename, subfolder, folder_type, base_url):
    log.info('get_image')
    data = {'filename': filename, 'subfolder': subfolder, 'type': folder_type}
    url_values = urllib.parse.urlencode(data)
    return f'{base_url}/view?{url_values}'


async def get_history(prompt_id, base_url, api_key):
    log.info('get_history')
    session = await get_session()
    async with session.get(
        f'{base_url}/history/{prompt_id}',
        headers={**default_headers, 'Authorization': f'Bearer {api_key}'},
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        r.raise_for_status()
        return await r.json()


async def _ws_get_images(ws, workflow, client_id, base_url, api_key):
    """Queue a prompt and wait on *ws* for ComfyUI to finish executing it.

    Returns a dict of ``{'data': [{'url': ...}, ...]}``.
    """
    queue_response = await queue_prompt(workflow, client_id, base_url, api_key)
    if not queue_response or 'prompt_id' not in queue_response:
        log.error(f'ComfyUI queue_prompt returned unexpected response: {queue_response}')
        raise RuntimeError(f'ComfyUI did not return a prompt_id. Response: {queue_response}')

    prompt_id = queue_response['prompt_id']
    output_images = []

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            message = json.loads(msg.data)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            log.error(f'WebSocket closed unexpectedly: {msg.type}')
            break
        # binary messages (previews) are silently skipped

    history_map = await get_history(prompt_id, base_url, api_key)
    history = history_map.get(prompt_id) if history_map else None
    if history is None:
        log.error(f'ComfyUI history missing for prompt_id={prompt_id}. Full response: {history_map}')
        return {'data': []}

    for node_id in history.get('outputs', {}):
        node_output = history['outputs'][node_id]
        if node_id in workflow and workflow[node_id].get('class_type') in [
            'SaveImage',
            'PreviewImage',
        ]:
            if 'images' in node_output:
                for image in node_output['images']:
                    url = get_image_url(image['filename'], image['subfolder'], image['type'], base_url)
                    output_images.append({'url': url})
    return {'data': output_images}


async def comfyui_upload_image(image_file_item, base_url, api_key):
    url = f'{base_url}/api/upload/image'
    headers = {}

    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    _, (filename, file_bytes, mime_type) = image_file_item

    form = aiohttp.FormData()
    form.add_field('image', file_bytes, filename=filename, content_type=mime_type)
    form.add_field('type', 'input')  # required by ComfyUI

    session = await get_session()
    async with session.post(url, data=form, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL) as resp:
        resp.raise_for_status()
        return await resp.json()


class ComfyUINodeInput(BaseModel):
    type: Optional[str] = None
    node_ids: list[str] = []
    key: Optional[str] = 'text'
    value: Optional[str] = None


class ComfyUIWorkflow(BaseModel):
    workflow: str
    nodes: list[ComfyUINodeInput]


class ComfyUICreateImageForm(BaseModel):
    workflow: ComfyUIWorkflow

    prompt: str
    negative_prompt: Optional[str] = None
    width: int
    height: int
    n: int = 1

    steps: Optional[int] = None
    seed: Optional[int] = None
    extra_params: Optional[dict] = None


def _apply_workflow_nodes(workflow, nodes, model, payload):
    """Mutate *workflow* dict in-place based on typed node definitions.

    Supports both the legacy hardcoded type strings (e.g. 'prompt', 'model',
    'width', 'height', 'steps', 'seed', 'image', 'n') and the new dynamic
    format produced by the auto-detection feature ('ClassName::inputKey').

    For the dynamic format, injection is decided by the *key* field (the
    ComfyUI input name), falling back to the ``node.value`` passthrough for
    any key that does not map to a known semantic slot.
    """
    for node in nodes:
        node_type = node.type or ''
        node_key = node.key or ''

        # --- Legacy semantic type names (backward compat) --------------------
        if node_type == 'model':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key] = model
        elif node_type == 'prompt':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'text'] = payload.prompt
        elif node_type == 'negative_prompt':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'text'] = payload.negative_prompt
        elif node_type == 'image':
            if isinstance(payload.image, list):
                for idx, node_id in enumerate(node.node_ids):
                    if idx < len(payload.image):
                        workflow[node_id]['inputs'][node_key] = payload.image[idx]
            else:
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node_key] = payload.image
        elif node_type == 'width':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'width'] = payload.width
        elif node_type == 'height':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'height'] = payload.height
        elif node_type == 'n':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'batch_size'] = payload.n
        elif node_type == 'steps':
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key if node_key else 'steps'] = payload.steps
        elif node_type == 'seed':
            seed = payload.seed if payload.seed else random.randint(0, 1125899906842624)
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key] = seed

        # --- New dynamic format: 'ClassName::inputKey' -----------------------
        elif '::' in node_type:
            # Derive semantic meaning from the key name
            for node_id in node.node_ids:
                if node_id not in workflow:
                    continue
                if node_key in ('ckpt_name', 'unet_name'):
                    # Model selection
                    workflow[node_id]['inputs'][node_key] = model
                elif node_key in ('text', 'prompt', 'positive'):
                    # Positive prompt text
                    workflow[node_id]['inputs'][node_key] = payload.prompt
                elif node_key in ('width',):
                    workflow[node_id]['inputs'][node_key] = payload.width
                elif node_key in ('height',):
                    workflow[node_id]['inputs'][node_key] = payload.height
                elif node_key in ('steps',):
                    if payload.steps is not None:
                        workflow[node_id]['inputs'][node_key] = payload.steps
                elif node_key in ('seed', 'noise_seed'):
                    seed = payload.seed if payload.seed else random.randint(0, 1125899906842624)
                    workflow[node_id]['inputs'][node_key] = seed
                elif node_key in ('batch_size',):
                    workflow[node_id]['inputs'][node_key] = payload.n
                elif node_key in ('image',):
                    if hasattr(payload, 'image'):
                        img = payload.image
                        if isinstance(img, list):
                            idx = node.node_ids.index(node_id)
                            if idx < len(img):
                                workflow[node_id]['inputs'][node_key] = img[idx]
                        else:
                            workflow[node_id]['inputs'][node_key] = img
                elif node.value is not None:
                    # Custom static override
                    workflow[node_id]['inputs'][node_key] = node.value
                elif hasattr(payload, 'extra_params') and payload.extra_params and node_key in payload.extra_params:
                    # API-provided dynamic override
                    workflow[node_id]['inputs'][node_key] = payload.extra_params[node_key]

        # --- Generic static value passthrough --------------------------------
        else:
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node_key] = node.value


async def comfyui_create_image(model: str, payload: ComfyUICreateImageForm, client_id, base_url, api_key):
    ws_url = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
    workflow = json.loads(payload.workflow.workflow)
    _apply_workflow_nodes(workflow, payload.workflow.nodes, model, payload)

    headers = {'Authorization': f'Bearer {api_key}'}
    session = await get_session()

    try:
        async with session.ws_connect(
            f'{ws_url}/ws?clientId={client_id}',
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as ws:
            log.info('WebSocket connection established.')
            log.info('Sending workflow to WebSocket server.')
            log.debug(f'Workflow: {workflow}')
            images = await _ws_get_images(ws, workflow, client_id, base_url, api_key)
    except aiohttp.WSServerHandshakeError as e:
        log.exception(f'Failed to connect to WebSocket server: {e}')
        return None
    except Exception as e:
        log.exception(f'Error during image generation: {e}')
        return None

    return images


class ComfyUIEditImageForm(BaseModel):
    workflow: ComfyUIWorkflow

    image: str | list[str]
    prompt: str
    width: Optional[int] = None
    height: Optional[int] = None
    n: Optional[int] = None

    steps: Optional[int] = None
    seed: Optional[int] = None


async def comfyui_edit_image(model: str, payload: ComfyUIEditImageForm, client_id, base_url, api_key):
    ws_url = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
    workflow = json.loads(payload.workflow.workflow)
    _apply_workflow_nodes(workflow, payload.workflow.nodes, model, payload)

    headers = {'Authorization': f'Bearer {api_key}'}
    session = await get_session()

    try:
        async with session.ws_connect(
            f'{ws_url}/ws?clientId={client_id}',
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as ws:
            log.info('WebSocket connection established.')
            log.info('Sending workflow to WebSocket server.')
            log.debug(f'Workflow: {workflow}')
            images = await _ws_get_images(ws, workflow, client_id, base_url, api_key)
    except aiohttp.WSServerHandshakeError as e:
        log.exception(f'Failed to connect to WebSocket server: {e}')
        return None
    except Exception as e:
        log.exception(f'Error during image editing: {e}')
        return None

    return images
