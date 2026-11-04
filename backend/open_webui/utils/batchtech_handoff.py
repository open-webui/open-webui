"""BatchTechUI: make sub-agent handoffs visible.

Wraps a delegate_task run and emits chat status events (action='handoff') when work is handed to another model,
and when it finishes. The UI turns these into a "who is working" chip with the model's logo spinning.
New file, so upstream merges never conflict with it.
"""

import logging
import time

log = logging.getLogger(__name__)


def _model_info(request, model_id: str) -> dict:
    model = (getattr(request.app.state, 'MODELS', None) or {}).get(model_id) or {}
    owned_by = model.get('owned_by') or ''
    connection_type = model.get('connection_type')
    # Ollama models are local; OpenAI-compatible connections are local only if the connection says so.
    local = owned_by == 'ollama' or connection_type == 'local'
    return {'model_id': model_id, 'model_name': model.get('name') or model_id, 'local': local}


async def _emit(emitter, info: dict, delegation_id: str, mode: str, done: bool, status: str, started_at: float):
    if not emitter:
        return
    where = 'local' if info['local'] else 'cloud'
    if not done:
        description = f'Handing off to {info["model_name"]} ({where})'
    elif status == 'completed':
        description = f'{info["model_name"]} ({where}) finished in {time.time() - started_at:.1f}s'
    else:
        description = f'{info["model_name"]} ({where}) did not finish ({status})'
    try:
        await emitter(
            {
                'type': 'status',
                'data': {
                    'action': 'handoff',
                    'description': description,
                    'done': done,
                    'status': status,
                    'delegation_id': delegation_id,
                    'mode': mode,
                    **info,
                },
            }
        )
    except Exception:
        log.exception('batchtech handoff status failed')


async def track(request, event_emitter, model_id: str, delegation_id: str, background: bool, coro):
    info = _model_info(request, model_id)
    mode = 'background' if background else 'foreground'
    started_at = time.time()
    await _emit(event_emitter, info, delegation_id, mode, False, 'working', started_at)
    status = 'error'
    try:
        result = await coro
        status = result.get('status', 'completed') if isinstance(result, dict) else 'completed'
        return result
    except Exception:
        status = 'error'
        raise
    except BaseException:  # cancelled
        status = 'interrupted'
        raise
    finally:
        await _emit(event_emitter, info, delegation_id, mode, True, status, started_at)
