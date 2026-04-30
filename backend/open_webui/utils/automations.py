"""
Automation utilities and unified scheduler.

RRULE helpers, scheduler worker loop, and execution logic.
Follows the utils/<feature>.py pattern (cf. utils/channels.py, utils/task.py).

The scheduler_worker_loop handles all time-based background work:
  - Automation execution (claim_due → execute)
  - Calendar event alerts (upcoming events → socket + webhook notifications)

Environment:
    SCHEDULER_POLL_INTERVAL             – seconds between polls (default: 10)
    CALENDAR_ALERT_LOOKAHEAD_MINUTES   – default alert window (default: 5)
"""

import asyncio
import logging
import os
import random
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from fastapi import Request
from starlette.datastructures import Headers

from open_webui.constants import ERROR_MESSAGES
from open_webui.models.automations import Automations, AutomationRuns, AutomationModel
from open_webui.models.chats import ChatForm, Chats
from open_webui.models.users import Users
from open_webui.utils.task import prompt_template
from open_webui.internal.db import get_async_db

log = logging.getLogger(__name__)

SCHEDULER_POLL_INTERVAL = int(os.getenv('SCHEDULER_POLL_INTERVAL', os.getenv('AUTOMATION_POLL_INTERVAL', '10')))
CALENDAR_ALERT_LOOKAHEAD_MINUTES = int(os.getenv('CALENDAR_ALERT_LOOKAHEAD_MINUTES', '10'))


####################
# RRULE Helpers
####################


def _resolve_tz(tz: str = None) -> Optional[ZoneInfo]:
    """Safely resolve a timezone string to ZoneInfo.

    Returns None (→ server-local fallback) when *tz* is empty, None,
    or an unrecognised IANA key.  Logs a warning on bad keys so
    misconfiguration is visible in the server logs.
    """
    if not tz:
        return None
    try:
        return ZoneInfo(tz)
    except (KeyError, Exception):
        log.warning('Unknown timezone %r — falling back to server time', tz)
        return None


def _parse_rule(s: str):
    """Parse RRULE with clock-aligned DTSTART for sub-daily frequencies.

    MINUTELY/HOURLY rules use a fixed epoch DTSTART (2000-01-01 00:00)
    so intervals snap to clock boundaries (e.g. every 5min = :00, :05, :10).
    """
    raw = s.replace('RRULE:', '')
    parts = dict(p.split('=', 1) for p in raw.split(';') if '=' in p)
    freq = parts.get('FREQ', '')

    if freq in ('MINUTELY', 'HOURLY'):
        epoch = datetime(2000, 1, 1, 0, 0, 0)
        return rrulestr(s, dtstart=epoch, ignoretz=True)
    return rrulestr(s, ignoretz=True)


def validate_rrule(s: str, tz: str = None) -> None:
    """Raise ValueError if the RRULE is malformed or exhausted.

    When *tz* is provided the "now" reference uses the user's local
    clock so that near-future schedules are not incorrectly rejected
    on servers whose system clock is ahead (e.g. UTC vs US timezones).
    """
    try:
        rule = _parse_rule(s)
    except Exception as e:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_INVALID_RRULE(e))
    zi = _resolve_tz(tz)
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    if rule.after(now) is None:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_NO_FUTURE_RUNS)


def next_run_ns(s: str, tz: str = None) -> Optional[int]:
    """Next occurrence as epoch nanoseconds, respecting user timezone."""
    zi = _resolve_tz(tz)
    now = datetime.now(zi) if zi else datetime.now()
    dt = _parse_rule(s).after(now.replace(tzinfo=None))
    if dt is None:
        return None
    if zi:
        dt = dt.replace(tzinfo=zi)
    return int(dt.timestamp() * 1_000_000_000)


def next_n_runs_ns(s: str, n: int = 5, tz: str = None) -> list[int]:
    """Compute next N occurrences for UI preview.

    Uses the user's timezone for the starting "now" so that the
    preview matches the user's local clock (same as next_run_ns).
    """
    zi = _resolve_tz(tz)
    rule = _parse_rule(s)
    result = []
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    dt = now
    for _ in range(n):
        dt = rule.after(dt)
        if not dt:
            break
        if zi:
            dt_tz = dt.replace(tzinfo=zi)
            result.append(int(dt_tz.timestamp() * 1_000_000_000))
        else:
            result.append(int(dt.timestamp() * 1_000_000_000))
    return result


def rrule_interval_seconds(s: str) -> Optional[int]:
    """Approximate interval between recurrences in seconds.

    Returns None for one-shot (COUNT=1) schedules or rules
    with fewer than two future occurrences.
    """
    if 'COUNT=1' in s:
        return None
    rule = _parse_rule(s)
    now = datetime.now()
    first = rule.after(now)
    if first is None:
        return None
    second = rule.after(first)
    if second is None:
        return None
    return int((second - first).total_seconds())


############################
# Worker Loop
############################


# Keep the old name as an alias so any stale imports still work.
async def automation_worker_loop(app) -> None:
    """Deprecated alias — use scheduler_worker_loop."""
    await scheduler_worker_loop(app)


async def scheduler_worker_loop(app) -> None:
    """Unified background scheduler for all time-based work.

    Handles:
      1. Automation execution  (ENABLE_AUTOMATIONS)
      2. Calendar event alerts (ENABLE_CALENDAR)

    Runs on every instance. Poll interval is configurable via
    SCHEDULER_POLL_INTERVAL env var (default: 10 seconds).
    """
    log.info(f'Scheduler worker started (poll interval: {SCHEDULER_POLL_INTERVAL}s)')
    while True:
        try:
            # ── Automations ──
            if getattr(app.state.config, 'ENABLE_AUTOMATIONS', False):
                try:
                    async with get_async_db() as db:
                        batch = await Automations.claim_due(int(time.time_ns()), limit=10, db=db)
                    if batch:
                        log.info(f'Claimed {len(batch)} due automation(s)')
                    for automation in batch:
                        asyncio.create_task(execute_automation(app, automation))
                except Exception:
                    log.exception('Scheduler: automation error')

            # ── Calendar Alerts ──
            if getattr(app.state.config, 'ENABLE_CALENDAR', False):
                try:
                    await _check_calendar_alerts(app)
                except Exception:
                    log.exception('Scheduler: calendar alert error')

        except Exception:
            log.exception('Scheduler worker error')

        # Jitter to spread load across instances
        await asyncio.sleep(SCHEDULER_POLL_INTERVAL + random.uniform(0, 2))


##########################
# Execute
####################


def _build_request(app) -> Request:
    """Build a minimal ASGI Request for chat_completion.

    Mirrors the mock-request pattern used in main.py lifespan
    (model pre-fetch, tool server init) for consistency.
    """
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.0'},
        'method': 'POST',
        'path': '/api/v1/automations/internal',
        'query_string': b'',
        'headers': Headers({}).raw,
        'client': ('127.0.0.1', 0),
        'server': ('127.0.0.1', 80),
        'scheme': 'http',
        'app': app,
    }
    request = Request(scope)
    # Ensure request.state is initialized with required attributes
    request.state.token = None
    request.state.enable_api_keys = False
    return request


def _resolve_model_tool_ids(app, model_id: str) -> list[str]:
    """Read model-attached tool_ids from model config.

    The frontend does this in Chat.svelte (model.info.meta.toolIds).
    The backend never auto-resolves them, so we must do it explicitly.
    """
    models = getattr(app.state, 'MODELS', {})
    model = models.get(model_id, {})
    tool_ids = model.get('info', {}).get('meta', {}).get('toolIds', [])
    return list(tool_ids) if tool_ids else []


def _resolve_model_features(app, model_id: str) -> dict:
    """Read model default features from model config.

    The frontend does this in Chat.svelte (model.info.meta.defaultFeatureIds
    + model.info.meta.capabilities). Enables features like web_search,
    code_interpreter, image_generation when the model has them as defaults
    AND the capability is enabled AND the admin has enabled the feature.
    """
    models = getattr(app.state, 'MODELS', {})
    model = models.get(model_id, {})
    meta = model.get('info', {}).get('meta', {})

    default_feature_ids = meta.get('defaultFeatureIds', [])
    if not default_feature_ids:
        return {}

    capabilities = meta.get('capabilities', {})
    config = app.state.config
    features = {}

    # code_interpreter is excluded: it requires the frontend event emitter
    # and does not work in headless backend execution.
    feature_checks = {
        'web_search': getattr(config, 'ENABLE_WEB_SEARCH', False),
        'image_generation': getattr(config, 'ENABLE_IMAGE_GENERATION', False),
    }

    for feature_id in default_feature_ids:
        if feature_id in feature_checks:
            # Feature must be: in defaultFeatureIds + capability enabled + admin enabled
            if capabilities.get(feature_id) and feature_checks[feature_id]:
                features[feature_id] = True

    return features


def _resolve_model_filter_ids(app, model_id: str) -> list[str]:
    """Read model default filter_ids from model config."""
    models = getattr(app.state, 'MODELS', {})
    model = models.get(model_id, {})
    filter_ids = model.get('info', {}).get('meta', {}).get('defaultFilterIds', [])
    return list(filter_ids) if filter_ids else []


def _resolve_model_terminal_id(app, model_id: str) -> Optional[str]:
    """Read model default terminal_id from model config.

    The frontend does this in Chat.svelte (model.info.meta.terminalId).
    """
    models = getattr(app.state, 'MODELS', {})
    model = models.get(model_id, {})
    return model.get('info', {}).get('meta', {}).get('terminalId') or None


async def _set_terminal_cwd(app, server_id: str, user, cwd: str, chat_id: str) -> None:
    """Set the working directory on a terminal server via the proxy.

    Routes through the open-webui terminal proxy endpoint so that
    auth headers, orchestrator policy routing, and X-User-Id are
    handled correctly — same path the frontend uses.
    """
    import aiohttp
    from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL

    connections = getattr(getattr(app, 'state', None), 'config', None)
    if connections is None:
        return
    connections = getattr(connections, 'TERMINAL_SERVER_CONNECTIONS', None) or []
    connection = next((c for c in connections if c.get('id') == server_id), None)
    if connection is None:
        log.warning(f'Terminal server {server_id} not found for CWD set')
        return

    base_url = (connection.get('url') or '').rstrip('/')
    if not base_url:
        return

    # Build target URL — route through orchestrator policy if configured
    policy_id = connection.get('policy_id')
    if connection.get('server_type') == 'orchestrator' and policy_id:
        target_url = f'{base_url}/p/{policy_id}/files/cwd'
    else:
        target_url = f'{base_url}/files/cwd'

    headers = {'Content-Type': 'application/json', 'X-User-Id': user.id}
    if chat_id:
        headers['X-Session-Id'] = chat_id

    auth_type = connection.get('auth_type', 'bearer')
    if auth_type == 'bearer':
        headers['Authorization'] = f'Bearer {connection.get("key", "")}'

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(
                target_url,
                json={'path': cwd},
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.warning(f'Failed to set terminal CWD to {cwd}: HTTP {resp.status} — {body[:200]}')
    except Exception as e:
        log.warning(f'Failed to set terminal CWD: {e}')


async def execute_automation(app, automation: AutomationModel) -> None:
    """Execute an automation through the full chat completion pipeline.

    Creates a real chat, then calls chat_completion exactly like the frontend:
    session_id + chat_id + message_id → async task → pipeline handles everything
    (filters, model params, knowledge/RAG, tools, DB saves, webhooks).
    """
    try:
        user = await Users.get_user_by_id(automation.user_id)
        if not user:
            await _record_run(automation.id, 'error', error='User not found')
            return

        prompt = prompt_template(automation.data['prompt'], user)
        model_id = automation.data['model_id']
        terminal_config = automation.data.get('terminal')

        # Generate proper UUIDs for messages (same as frontend)
        user_msg_id = str(uuid4())
        assistant_msg_id = str(uuid4())

        chat_id = str(uuid4())
        chat = await Chats.insert_new_chat(
            chat_id,
            automation.user_id,
            ChatForm(
                chat={
                    'title': automation.name,
                    'models': [model_id],
                    'history': {
                        'currentId': assistant_msg_id,
                        'messages': {
                            user_msg_id: {
                                'id': user_msg_id,
                                'parentId': None,
                                'role': 'user',
                                'content': prompt,
                                'childrenIds': [assistant_msg_id],
                                'timestamp': int(time.time()),
                                'models': [model_id],
                            },
                            assistant_msg_id: {
                                'id': assistant_msg_id,
                                'parentId': user_msg_id,
                                'role': 'assistant',
                                'content': '',
                                'done': False,
                                'model': model_id,
                                'childrenIds': [],
                                'timestamp': int(time.time()),
                            },
                        },
                    },
                    'messages': [
                        {'role': 'user', 'content': prompt},
                    ],
                    'meta': {'automation_id': automation.id},
                }
            ),
        )

        if not chat:
            await _record_run(automation.id, 'error', error='Failed to create chat')
            return

        # Notify frontend to refresh chat list
        from open_webui.socket.main import sio

        await sio.emit(
            'events',
            {
                'chat_id': chat.id,
                'message_id': user_msg_id,
                'data': {'type': 'chat:list'},
            },
            room=f'user:{automation.user_id}',
        )

        # Resolve model defaults (frontend does this, backend doesn't)
        tool_ids = _resolve_model_tool_ids(app, model_id)
        features = _resolve_model_features(app, model_id)
        filter_ids = _resolve_model_filter_ids(app, model_id)

        # Resolve terminal from model config
        terminal_id = _resolve_model_terminal_id(app, model_id)

        # Build the same payload the frontend sends to /api/chat/completions
        form_data = {
            'model': model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': True,
            'chat_id': chat.id,
            'id': assistant_msg_id,
            'parent_id': None,  # Root message (chat already created above)
            'user_message': {
                'id': user_msg_id,
                'parentId': None,
                'role': 'user',
                'content': prompt,
            },
            'session_id': f'automation:{automation.id}',
            'background_tasks': {},
        }
        if tool_ids:
            form_data['tool_ids'] = tool_ids
        if features:
            form_data['features'] = features
        if filter_ids:
            form_data['filter_ids'] = filter_ids
        if terminal_id:
            form_data['terminal_id'] = terminal_id

        # Call the full chat completion pipeline (same as POST /api/chat/completions).
        # The handler reference is stored on app.state to avoid circular imports.
        request = _build_request(app)
        await app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)

        # Notify user
        from open_webui.socket.main import sio

        await sio.emit(
            'automation:result',
            {
                'automation_id': automation.id,
                'name': automation.name,
                'chat_id': chat.id,
                'status': 'success',
            },
            room=f'user:{automation.user_id}',
        )

        await _record_run(automation.id, 'success', chat_id=chat.id)

    except Exception as e:
        log.exception(f'Automation {automation.id} failed')
        await _record_run(automation.id, 'error', error=str(e)[:4000])


####################
# Internals
####################


async def _check_calendar_alerts(app) -> None:
    """Check for upcoming calendar events and send alert notifications.

    De-duplication is DB-backed via meta.alerted_at — survives restarts
    and works across multiple instances.
    """
    from open_webui.models.calendar import CalendarEvents, CalendarEventUpdateForm
    from open_webui.socket.main import sio

    now_ns = int(time.time_ns())
    default_lookahead_ns = CALENDAR_ALERT_LOOKAHEAD_MINUTES * 60 * 1_000_000_000

    async with get_async_db() as db:
        upcoming = await CalendarEvents.get_upcoming_events(now_ns, default_lookahead_ns, db=db)

    if not upcoming:
        return

    for event, user_tz in upcoming:
        # Skip if already alerted for this start time
        if event.meta and event.meta.get('alerted_at'):
            continue

        # Compute minutes until event starts
        minutes_until = max(0, int((event.start_at - now_ns) / (60 * 1_000_000_000)))

        alert_data = {
            'event_id': event.id,
            'title': event.title,
            'description': event.description or '',
            'start_at': event.start_at,
            'minutes_until': minutes_until,
            'calendar_id': event.calendar_id,
            'location': event.location or '',
        }

        await sio.emit(
            'events',
            {
                'data': {
                    'type': 'calendar:alert',
                    'data': alert_data,
                },
            },
            room=f'user:{event.user_id}',
        )

        # Mark as alerted in DB so it survives restarts / multi-instance
        try:
            await CalendarEvents.update_event_by_id(
                event.id,
                CalendarEventUpdateForm(meta={'alerted_at': now_ns}),
            )
        except Exception:
            log.debug(f'Failed to mark event {event.id} as alerted', exc_info=True)

        # Send webhook notification if user has one configured
        try:
            webui_name = getattr(app.state, 'WEBUI_NAME', 'Open WebUI')
            enable_user_webhooks = getattr(app.state.config, 'ENABLE_USER_WEBHOOKS', False)

            if enable_user_webhooks:
                user = await Users.get_user_by_id(event.user_id)
                if user and user.settings:
                    webhook_url = (
                        user.settings.get('ui', {}).get('notifications', {}).get('webhook_url', None)
                        if isinstance(user.settings, dict)
                        else getattr(getattr(user.settings, 'ui', None), 'get', lambda *a: None)(
                            'notifications', {}
                        ).get('webhook_url', None)
                        if hasattr(user.settings, 'ui')
                        else None
                    )
                    if webhook_url:
                        from open_webui.utils.webhook import post_webhook

                        time_str = f'in {minutes_until} min' if minutes_until > 0 else 'now'
                        await post_webhook(
                            webui_name,
                            webhook_url,
                            f'{event.title} — starting {time_str}',
                            {
                                'action': 'calendar_alert',
                                'title': event.title,
                                'minutes_until': minutes_until,
                                'event_id': event.id,
                            },
                        )
        except Exception:
            log.debug(f'Failed to send webhook for calendar alert {event.id}', exc_info=True)


async def _record_run(
    automation_id: str,
    status: str,
    chat_id: str = None,
    error: str = None,
):
    """Insert a run record into automation_run."""
    async with get_async_db() as db:
        await AutomationRuns.insert(automation_id, status, chat_id=chat_id, error=error, db=db)
