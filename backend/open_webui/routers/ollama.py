"""Ollama router compatibility wrapper with custom local-inference performance controls.

The upstream router is kept verbatim in ``ollama_legacy.py`` so this fork can layer
production customizations without carrying a large, conflict-prone copy of the
upstream implementation.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Request
from pydantic import BaseModel, Field

from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user
from open_webui.utils.json_codec import JSONCodec
from open_webui.routers import ollama_legacy as _legacy

# Re-export the upstream router and public API. Module __getattr__ below keeps
# imports from open_webui.routers.ollama backward compatible.
router = _legacy.router

_PERF_KEYS = {
    'keep_alive': 'ollama.performance.keep_alive',
    'flash_attention': 'ollama.performance.flash_attention',
    'num_parallel': 'ollama.performance.num_parallel',
}
_NATIVE_KEEP_ALIVE_ENDPOINTS = ('/api/chat', '/api/generate', '/api/embed', '/api/embeddings')
_original_send_request = _legacy.send_request


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


async def _performance_values() -> dict[str, Any]:
    values = await Config.get_many(*_PERF_KEYS.values())
    keep_alive = values.get(_PERF_KEYS['keep_alive'])
    flash_attention = values.get(_PERF_KEYS['flash_attention'])
    num_parallel = values.get(_PERF_KEYS['num_parallel'])
    return {
        'OLLAMA_KEEP_ALIVE': keep_alive if keep_alive is not None else os.getenv('OLLAMA_KEEP_ALIVE', '-1'),
        'OLLAMA_FLASH_ATTENTION': (
            flash_attention if flash_attention is not None else _env_bool('OLLAMA_FLASH_ATTENTION', True)
        ),
        'OLLAMA_NUM_PARALLEL': int(
            num_parallel if num_parallel is not None else os.getenv('OLLAMA_NUM_PARALLEL', '2')
        ),
    }


async def send_request(
    url: str,
    method: str = 'POST',
    *,
    payload=None,
    **kwargs,
):
    """Inject the persisted keep-alive default into native inference requests.

    Explicit caller values (notably ``keep_alive: 0`` used by unload) always win.
    """
    if method.upper() == 'POST' and payload is not None and url.endswith(_NATIVE_KEEP_ALIVE_ENDPOINTS):
        try:
            was_bytes = isinstance(payload, (bytes, bytearray))
            raw = payload.decode('utf-8') if was_bytes else payload
            body = JSONCodec.loads(raw) if isinstance(raw, str) else raw
            if isinstance(body, dict) and body.get('keep_alive') is None:
                body['keep_alive'] = (await _performance_values())['OLLAMA_KEEP_ALIVE']
                encoded = JSONCodec.dumps(body)
                payload = encoded.encode('utf-8') if was_bytes else encoded
        except Exception as exc:
            _legacy.log.warning('Unable to apply Ollama keep_alive default: %s', exc)

    return await _original_send_request(url, method, payload=payload, **kwargs)


# Existing upstream route functions resolve ``send_request`` from the legacy
# module's globals at call time, so replacing it here applies the behavior to
# chat/generate/embed without rewriting upstream route definitions.
_legacy.send_request = send_request


class OllamaPerformanceConfigForm(BaseModel):
    OLLAMA_KEEP_ALIVE: str = '-1'
    OLLAMA_FLASH_ATTENTION: bool = True
    OLLAMA_NUM_PARALLEL: int = Field(default=2, ge=1, le=16)


@router.get('/performance')
async def get_performance_config(user=Depends(get_admin_user)) -> dict:
    values = await _performance_values()
    return {
        **values,
        'KEEP_MODELS_LOADED': str(values['OLLAMA_KEEP_ALIVE']).strip().startswith('-'),
        'RECOMMENDED_NUM_PARALLEL_MIN': 2,
        'RECOMMENDED_NUM_PARALLEL_MAX': 4,
        'SERVER_RESTART_REQUIRED_FOR': ['OLLAMA_FLASH_ATTENTION', 'OLLAMA_NUM_PARALLEL'],
    }


@router.post('/performance/update')
async def update_performance_config(
    form_data: OllamaPerformanceConfigForm,
    user=Depends(get_admin_user),
) -> dict:
    # The UI intentionally maps its keep-loaded toggle to -1 / 5m. Accept a
    # duration string here for API/admin automation compatibility.
    keep_alive = form_data.OLLAMA_KEEP_ALIVE.strip() or '5m'
    await Config.upsert(
        {
            _PERF_KEYS['keep_alive']: keep_alive,
            _PERF_KEYS['flash_attention']: form_data.OLLAMA_FLASH_ATTENTION,
            _PERF_KEYS['num_parallel']: form_data.OLLAMA_NUM_PARALLEL,
        }
    )
    return await get_performance_config(user)


def _expiry_is_effectively_forever(expires_at: Any) -> bool:
    if not expires_at:
        return False
    try:
        parsed = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        # Ollama represents an indefinitely retained runner with a far-future
        # expiry. Ten years is safely beyond every normal keep-alive duration.
        return parsed > datetime.now(timezone.utc) + timedelta(days=3650)
    except (TypeError, ValueError):
        return str(expires_at).lower() in {'forever', 'infinite', 'infinity'}


@router.get('/performance/diagnostics')
async def get_performance_diagnostics(
    request: Request,
    user=Depends(get_admin_user),
) -> dict:
    performance = await _performance_values()
    loaded = await _legacy.get_ollama_loaded_models(request, user=user)
    models = []
    for model in loaded.get('models', []):
        expires_at = model.get('expires_at')
        forever = _expiry_is_effectively_forever(expires_at)
        models.append(
            {
                **model,
                'until': 'Forever' if forever else expires_at,
                'keep_alive_forever': forever,
            }
        )

    configured_forever = str(performance['OLLAMA_KEEP_ALIVE']).strip().startswith('-')
    finite_models = [model['model'] for model in models if not model['keep_alive_forever']]
    return {
        'models': models,
        'configured_keep_alive': performance['OLLAMA_KEEP_ALIVE'],
        'configured_forever': configured_forever,
        'finite_models': finite_models,
        'warning': (
            'One or more loaded models have a finite expiry. Send a new inference request after enabling keep-loaded mode.'
            if configured_forever and finite_models
            else None
        ),
    }


def __getattr__(name: str):
    return getattr(_legacy, name)
