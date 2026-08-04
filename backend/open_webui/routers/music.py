"""Music router — music generation endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.events import EVENTS, publish_event
from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)
router = APIRouter()

# --- Constants ---

MUSIC_MODELS = {
    'generation': ['music-3.0', 'music-2.6', 'music-3.0-free', 'music-2.6-free'],
    'cover': ['music-cover', 'music-cover-free'],
}

MUSIC_DEFAULT_MODEL = MUSIC_MODELS['generation'][0]

MUSIC_OUTPUT_FORMATS = ('url', 'hex')

MUSIC_CONFIG_KEYS = {
    'API_KEY': 'audio.music.minimax.api_key',
    'API_BASE_URL': 'audio.music.minimax.api_base_url',
    'MODEL': 'audio.music.model',
}


async def get_config_values(key_map: dict[str, str]) -> dict:
    values = await Config.get_many(*key_map.values())
    return {field: values[storage_key] for field, storage_key in key_map.items() if storage_key in values}


def config_updates(data: dict, key_map: dict[str, str]) -> dict:
    return {key_map[field]: value for field, value in data.items() if field in key_map}


class MusicConfigForm(BaseModel):
    API_KEY: str = ''
    API_BASE_URL: str = 'https://api.minimax.io/v1'
    MODEL: str = MUSIC_DEFAULT_MODEL


class MusicGenerationForm(BaseModel):
    model: str = ''
    prompt: str = ''
    lyrics: str = ''
    stream: bool = False
    output_format: str = 'url'
    audio_setting: Optional[dict] = None
    lyrics_optimizer: bool = False
    is_instrumental: bool = False
    audio_url: str = ''
    audio_base64: str = ''
    cover_feature_id: str = ''
    aigc_watermark: bool = False


@router.get('/config')
async def get_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(MUSIC_CONFIG_KEYS)


@router.post('/config/update')
async def update_config(request: Request, form_data: MusicConfigForm, user=Depends(get_admin_user)):
    await Config.upsert(config_updates(form_data.model_dump(), MUSIC_CONFIG_KEYS))
    return await get_config(request, user)


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    return {
        'default_model': MUSIC_DEFAULT_MODEL,
        'models': [
            {'id': model, 'task': task}
            for task, models in MUSIC_MODELS.items()
            for model in models
        ],
    }


async def _raise_music_error(exc: Exception, r=None) -> None:
    """Raise a standardised HTTPException from a music provider failure."""
    code = r.status if r is not None else 500
    detail = 'Open WebUI: Server Connection Error'
    if r is not None:
        try:
            res = await r.json()
            if 'error' in res:
                msg = res['error']
                detail = f'External: {msg.get("message", msg) if isinstance(msg, dict) else msg}'
            elif 'message' in res:
                detail = f'External: {res["message"]}'
        except Exception:
            detail = f'External: {exc}'
    raise HTTPException(status_code=code, detail=detail)


@router.post('/generations')
async def generate_music(request: Request, form_data: MusicGenerationForm, user=Depends(get_verified_user)):
    api_key = await Config.get('audio.music.minimax.api_key')
    api_base_url = (await Config.get('audio.music.minimax.api_base_url') or 'https://api.minimax.io/v1').rstrip('/')

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='MiniMax API key is required for music generation',
        )

    model = form_data.model or await Config.get('audio.music.model') or MUSIC_DEFAULT_MODEL

    output_format = form_data.output_format or 'url'
    if output_format not in MUSIC_OUTPUT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported output format: {output_format}',
        )

    is_cover = model.startswith('music-cover') or bool(form_data.audio_url) or bool(form_data.audio_base64)
    if is_cover and not (form_data.audio_url or form_data.audio_base64):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='A music cover request requires one of audio_url or audio_base64',
        )
    if form_data.audio_url and form_data.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Provide either audio_url or audio_base64, not both',
        )

    payload = {'model': model, 'output_format': output_format}
    if form_data.prompt:
        payload['prompt'] = form_data.prompt
    if form_data.lyrics:
        payload['lyrics'] = form_data.lyrics
    if form_data.stream:
        payload['stream'] = True
    if form_data.audio_setting:
        payload['audio_setting'] = form_data.audio_setting
    if form_data.lyrics_optimizer:
        payload['lyrics_optimizer'] = True
    if form_data.is_instrumental:
        payload['is_instrumental'] = True
    if form_data.audio_url:
        payload['audio_url'] = form_data.audio_url
    if form_data.audio_base64:
        payload['audio_base64'] = form_data.audio_base64
    if form_data.cover_feature_id:
        payload['cover_feature_id'] = form_data.cover_feature_id
    if form_data.aigc_watermark:
        payload['aigc_watermark'] = True

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    if ENABLE_FORWARD_USER_INFO_HEADERS:
        headers = include_user_info_headers(headers, user)

    r = None
    try:
        session = await get_session()
        r = await session.post(
            url=f'{api_base_url}/music_generation',
            json=payload,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        r.raise_for_status()
        res = await r.json(content_type=None)
    except Exception as exc:
        log.exception(exc)
        await _raise_music_error(exc, r)

    base_resp = res.get('base_resp') or {}
    if base_resp.get('status_code', 0) != 0:
        detail = base_resp.get('status_msg') or 'MiniMax music generation request failed'
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'External: {detail}')

    data = res.get('data') or {}
    generation_status = data.get('status')
    audio = data.get('audio')

    await publish_event(
        request,
        EVENTS.MUSIC_GENERATION_REQUESTED,
        actor=user,
        subject_id=model,
        data={
            'model': model,
            'output_format': output_format,
            'prompt_preview': str(form_data.prompt or form_data.lyrics or '')[:300],
            'status': generation_status,
        },
    )

    return {
        'status': generation_status,
        'in_progress': generation_status == 1,
        'output_format': output_format,
        'model': model,
        'audio': audio,
    }
