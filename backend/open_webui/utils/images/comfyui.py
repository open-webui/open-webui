import asyncio
import logging
import mimetypes
import random
import urllib.parse
from typing import Optional

import aiohttp
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.session_pool import get_session
from pydantic import BaseModel

log = logging.getLogger(__name__)

default_headers = {'User-Agent': 'Mozilla/5.0'}


async def queue_prompt(prompt, client_id, base_url, api_key):
    log.info('queue_prompt')
    p = {'prompt': prompt, 'client_id': client_id}
    log.debug('queue_prompt data: %s', p)
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


async def _ws_run_prompt(ws, workflow, client_id, base_url, api_key) -> dict:
    """Queue a prompt, wait on *ws* for ComfyUI to finish executing it, and return its history entry.

    Raises when the workflow failed.
    """
    prompt_id = (await queue_prompt(workflow, client_id, base_url, api_key))['prompt_id']

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            message = JSONCodec.loads(msg.data)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            log.error(f'WebSocket closed unexpectedly: {msg.type}')
            break
        # binary messages (previews) are silently skipped

    history = (await get_history(prompt_id, base_url, api_key))[prompt_id]
    status = history.get('status', {})
    if status.get('status_str') == 'error':
        error = next((data for kind, data in status.get('messages', []) if kind == 'execution_error'), {})
        raise Exception(
            f'ComfyUI {error.get("node_type", "workflow")} failed: {error.get("exception_message", "").strip()}'
        )
    return history


async def _ws_get_images(ws, workflow, client_id, base_url, api_key):
    """Queue a prompt and wait on *ws* for ComfyUI to finish executing it.

    Returns a dict of ``{'data': [{'url': ...}, ...]}``.
    """
    history = await _ws_run_prompt(ws, workflow, client_id, base_url, api_key)
    output_images = []

    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if node_id in workflow and workflow[node_id].get('class_type') in [
            'SaveImage',
            'SaveImageAdvanced',
            'SaveAnimatedWEBP',
            'SaveAnimatedPNG',
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


# Node types filled from the request field of the same name, with the input key used when none is set.
WORKFLOW_NODE_INPUT_KEYS = {
    'prompt': 'text',
    'negative_prompt': 'text',
    'width': 'width',
    'height': 'height',
    'n': 'batch_size',
    'steps': 'steps',
    'length': 'length',
    'fps': 'fps',
}


def _apply_workflow_nodes(workflow, nodes, model, payload):
    """Mutate *workflow* dict in-place based on typed node definitions.

    A value the request leaves out (None) keeps the one already in the workflow.
    """

    def set_input(node, value, default_key=None):
        if value is None:
            return
        for node_id in node.node_ids:
            workflow[node_id]['inputs'][node.key or default_key] = value

    for node in nodes:
        if not node.type:
            set_input(node, node.value)
        elif node.type == 'model':
            # No model (a connection without model IDs) runs the one the workflow sets.
            set_input(node, model or None)
        elif node.type == 'image':
            image = getattr(payload, 'image', None)
            if isinstance(image, list):
                for node_id, value in zip(node.node_ids, image):
                    workflow[node_id]['inputs'][node.key] = value
            else:
                set_input(node, image)
        elif node.type == 'seed':
            set_input(node, getattr(payload, 'seed', None) or random.randint(0, 1125899906842624))
        elif node.type in WORKFLOW_NODE_INPUT_KEYS:
            set_input(node, getattr(payload, node.type, None), WORKFLOW_NODE_INPUT_KEYS[node.type])


async def comfyui_create_image(model: str, payload: ComfyUICreateImageForm, client_id, base_url, api_key):
    ws_url = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
    workflow = JSONCodec.loads(payload.workflow.workflow)
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
            log.debug('Workflow: %s', workflow)
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
    workflow = JSONCodec.loads(payload.workflow.workflow)
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
            log.debug('Workflow: %s', workflow)
            images = await _ws_get_images(ws, workflow, client_id, base_url, api_key)
    except aiohttp.WSServerHandshakeError as e:
        log.exception(f'Failed to connect to WebSocket server: {e}')
        return None
    except Exception as e:
        log.exception(f'Error during image editing: {e}')
        return None

    return images


class ComfyUICreateVideoForm(BaseModel):
    workflow: ComfyUIWorkflow

    prompt: str
    negative_prompt: Optional[str] = None
    image: Optional[str] = None  # starting frame, as a file name uploaded to ComfyUI
    width: Optional[int] = None
    height: Optional[int] = None
    length: Optional[int] = None  # in frames
    fps: Optional[float] = None

    steps: Optional[int] = None
    seed: Optional[int] = None


VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mkv', '.mov', '.gif', '.webp')


def get_video_outputs(history: dict) -> list[dict]:
    """The video files a finished prompt saved, as ``{filename, subfolder, type}`` entries.

    ComfyUI's SaveVideo and SaveWEBM list them under ``images`` (marked ``animated``), and
    VideoHelperSuite's Video Combine under ``gifs``. Inputs a workflow loaded (LoadVideo) are left out.
    """
    outputs = []
    for node_output in (history.get('outputs') or {}).values():
        for key in ('images', 'gifs', 'videos'):
            for entry in node_output.get(key) or []:
                if (
                    isinstance(entry, dict)
                    and entry.get('filename', '').lower().endswith(VIDEO_EXTENSIONS)
                    and entry.get('type') != 'input'
                ):
                    outputs.append(entry)
    # Prefer saved files over the temporary previews some nodes also write.
    saved = [entry for entry in outputs if entry.get('type') == 'output']
    return saved or outputs


async def get_video(entry: dict, base_url: str, api_key: str) -> tuple[bytes, str]:
    """Download a video ComfyUI saved, with its content type."""
    data = {'filename': entry['filename'], 'subfolder': entry.get('subfolder', ''), 'type': entry.get('type', 'output')}
    headers = {**default_headers}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    session = await get_session()
    async with session.get(
        f'{base_url}/view?{urllib.parse.urlencode(data)}', headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL
    ) as r:
        r.raise_for_status()
        content_type = r.headers.get('content-type', '').split(';')[0]
        if not content_type.startswith(('video/', 'image/')):
            content_type = mimetypes.guess_type(entry['filename'])[0] or 'video/mp4'
        return await r.read(), content_type


async def comfyui_create_video(
    model: str, payload: ComfyUICreateVideoForm, client_id, base_url, api_key, timeout: float
) -> list[tuple[bytes, str]]:
    """Run a video workflow and return each video it saved, as ``(data, content_type)``.

    Raises when the workflow fails, saves no video, or is not done within *timeout* seconds.
    """
    ws_url = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
    workflow = JSONCodec.loads(payload.workflow.workflow)
    _apply_workflow_nodes(workflow, payload.workflow.nodes, model, payload)
    log.debug('Workflow: %s', workflow)

    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    session = await get_session()
    try:
        async with asyncio.timeout(timeout):
            async with session.ws_connect(
                f'{ws_url}/ws?clientId={client_id}',
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as ws:
                history = await _ws_run_prompt(ws, workflow, client_id, base_url, api_key)
    except TimeoutError:
        raise Exception(f'The video was not ready after {int(timeout)} seconds')

    outputs = get_video_outputs(history)
    if not outputs:
        raise Exception('The ComfyUI workflow saved no video. Add a Save Video node to it.')
    return [await get_video(entry, base_url, api_key) for entry in outputs]
