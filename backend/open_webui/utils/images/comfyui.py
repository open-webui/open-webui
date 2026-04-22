import json
import logging
import random
import urllib.parse
from typing import Optional

import aiohttp
from pydantic import BaseModel

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

default_headers = {'User-Agent': 'Mozilla/5.0'}


async def queue_prompt(prompt, client_id, base_url, api_key):
    log.info('queue_prompt')
    p = {'prompt': prompt, 'client_id': client_id}
    log.debug(f'queue_prompt data: {p}')
    try:
        session = await get_session()
        async with session.post(
            f'{base_url}/prompt',
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
    prompt_id = (await queue_prompt(workflow, client_id, base_url, api_key))['prompt_id']
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

    history = (await get_history(prompt_id, base_url, api_key))[prompt_id]
    for node_id in history['outputs']:
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


def _apply_workflow_nodes(workflow, nodes, model, payload):
    """Mutate *workflow* dict in-place based on typed node definitions."""
    for node in nodes:
        if node.type:
            if node.type == 'model':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key] = model
            elif node.type == 'prompt':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'text'] = payload.prompt
            elif node.type == 'negative_prompt':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'text'] = payload.negative_prompt
            elif node.type == 'image':
                if isinstance(payload.image, list):
                    for idx, node_id in enumerate(node.node_ids):
                        if idx < len(payload.image):
                            workflow[node_id]['inputs'][node.key] = payload.image[idx]
                else:
                    for node_id in node.node_ids:
                        workflow[node_id]['inputs'][node.key] = payload.image
            elif node.type == 'width':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'width'] = payload.width
            elif node.type == 'height':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'height'] = payload.height
            elif node.type == 'n':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'batch_size'] = payload.n
            elif node.type == 'steps':
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key if node.key else 'steps'] = payload.steps
            elif node.type == 'seed':
                seed = payload.seed if payload.seed else random.randint(0, 1125899906842624)
                for node_id in node.node_ids:
                    workflow[node_id]['inputs'][node.key] = seed
        else:
            for node_id in node.node_ids:
                workflow[node_id]['inputs'][node.key] = node.value


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
            log.info(f'Workflow: {workflow}')
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
            log.info(f'Workflow: {workflow}')
            images = await _ws_get_images(ws, workflow, client_id, base_url, api_key)
    except aiohttp.WSServerHandshakeError as e:
        log.exception(f'Failed to connect to WebSocket server: {e}')
        return None
    except Exception as e:
        log.exception(f'Error during image editing: {e}')
        return None

    return images
