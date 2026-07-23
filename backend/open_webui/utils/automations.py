"""
Automation utilities and unified scheduler.

RRULE helpers, scheduler worker loop, and execution logic.
Follows the utils/<feature>.py pattern (cf. utils/channels.py, utils/task.py).

The scheduler_worker_loop handles all time-based background work:
  - Automation execution (claim_due → execute)
  - Calendar event alerts (upcoming events → socket + webhook notifications)
  - One-shot chat timers

Environment:
    SCHEDULER_POLL_INTERVAL             – seconds between polls (default: 10)
    TIMER_POLL_INTERVAL                 – seconds between timer polls (default: 1)
    CALENDAR_ALERT_LOOKAHEAD_MINUTES   – default alert window (default: 5)
"""

import asyncio
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db
from open_webui.models.automations import AutomationModel, AutomationRuns, Automations
from open_webui.models.chats import ChatForm, Chats
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.utils.auth import create_token
from open_webui.utils.misc import parse_duration
from open_webui.utils.task import prompt_template
from open_webui.utils.terminals import get_terminal_server_url
from starlette.datastructures import Headers

log = logging.getLogger(__name__)

SCHEDULER_POLL_INTERVAL = int(os.getenv('SCHEDULER_POLL_INTERVAL', os.getenv('AUTOMATION_POLL_INTERVAL', '10')))
TIMER_POLL_INTERVAL = int(os.getenv('TIMER_POLL_INTERVAL', '1'))
CALENDAR_ALERT_LOOKAHEAD_MINUTES = int(os.getenv('CALENDAR_ALERT_LOOKAHEAD_MINUTES', '10'))
AUTOMATION_COMPLETION_TIMEOUT = max(30, int(os.getenv('AUTOMATION_COMPLETION_TIMEOUT', '1800')))


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


def _parse_rule(s: str, now: Optional[datetime] = None):
    """Parse RRULE with clock-aligned DTSTART for sub-daily frequencies.

    MINUTELY/HOURLY rules use a fixed epoch DTSTART (2000-01-01 00:00)
    so intervals snap to clock boundaries (e.g. every 5min = :00, :05, :10).
    """
    raw = s.replace('RRULE:', '')
    parts = dict(p.split('=', 1) for p in raw.split(';') if '=' in p)
    freq = parts.get('FREQ', '')

    if freq in ('MINUTELY', 'HOURLY'):
        epoch = datetime(2000, 1, 1, 0, 0, 0)
        if (
            now is not None
            and s.startswith('RRULE:')
            and '\n' not in s
            and '\r' not in s
            and set(parts) <= {'FREQ', 'INTERVAL', 'BYMINUTE', 'BYSECOND'}
        ):
            try:
                interval = int(parts.get('INTERVAL', '1'))
                if interval > 0:
                    step = timedelta(minutes=interval) if freq == 'MINUTELY' else timedelta(hours=interval)
                    return rrulestr(s, dtstart=epoch + ((now - epoch) // step) * step, ignoretz=True)
            except (TypeError, ValueError):
                pass
        return rrulestr(s, dtstart=epoch, ignoretz=True)
    return rrulestr(s, ignoretz=True)


def validate_rrule(s: str, tz: str = None) -> None:
    """Raise ValueError if the RRULE is malformed or exhausted.

    When *tz* is provided the "now" reference uses the user's local
    clock so that near-future schedules are not incorrectly rejected
    on servers whose system clock is ahead (e.g. UTC vs US timezones).
    """
    zi = _resolve_tz(tz)
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    try:
        rule = _parse_rule(s, now)
    except Exception as e:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_INVALID_RRULE(e))
    if rule.after(now) is None:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_NO_FUTURE_RUNS)


def next_run_ns(s: str, tz: str = None) -> Optional[int]:
    """Next occurrence as epoch nanoseconds, respecting user timezone."""
    zi = _resolve_tz(tz)
    now = datetime.now(zi) if zi else datetime.now()
    now_naive = now.replace(tzinfo=None)
    dt = _parse_rule(s, now_naive).after(now_naive)
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
    result = []
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    rule = _parse_rule(s, now)
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
    now = datetime.now()
    rule = _parse_rule(s, now)
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
    log.info(
        f'Scheduler worker started (timer poll interval: {TIMER_POLL_INTERVAL}s, '
        f'scheduler poll interval: {SCHEDULER_POLL_INTERVAL}s)'
    )
    next_scheduler_poll = 0.0

    while True:
        try:
            now = time.monotonic()
            # ── Timers ──
            try:
                from open_webui.utils.timers import claim_due_timers, execute_due_timer

                for timer_id, claim_id in await claim_due_timers(int(time.time_ns()), limit=10):
                    asyncio.create_task(execute_due_timer(app, timer_id, claim_id))
            except Exception:
                log.exception('Scheduler: timer error')

            if now < next_scheduler_poll:
                await asyncio.sleep(max(1, TIMER_POLL_INTERVAL))
                continue
            # Jitter to spread automation/calendar load across instances; timers keep a tight poll.
            next_scheduler_poll = now + SCHEDULER_POLL_INTERVAL + random.uniform(0, 2)

            # ── Automations ──
            if await Config.get('automations.enable'):
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
            if await Config.get('calendar.enable'):
                try:
                    await _check_calendar_alerts(app)
                except Exception:
                    log.exception('Scheduler: calendar alert error')

        except Exception:
            log.exception('Scheduler worker error')

        await asyncio.sleep(max(1, TIMER_POLL_INTERVAL))


##########################
# Execute
####################


def _build_request(
    app,
    token: Optional[str] = None,
) -> Request:
    """Build a minimal ASGI Request for chat_completion.

    Mirrors the mock-request pattern used in main.py lifespan
    (model pre-fetch, tool server init) for consistency.

    When token is provided, attach it as
    request.state.token so session-auth tool servers and terminals can
    authenticate headless scheduled runs as the automation owner.
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
    request.state.token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token) if token else None
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


def _has_final_assistant_message(message: dict) -> bool:
    """Return whether a terminal assistant row contains visible final text."""
    output = message.get('output')
    if not isinstance(output, list):
        return False

    return any(
        isinstance(item, dict)
        and item.get('type') == 'message'
        and any(
            isinstance(content, dict) and content.get('type') == 'output_text' and str(content.get('text', '')).strip()
            for content in item.get('content', [])
        )
        for item in output
    )


async def _wait_for_automation_completion(chat_id: str, message_id: str) -> dict:
    """Wait for the detached chat task and validate its persisted result."""
    deadline = time.monotonic() + AUTOMATION_COMPLETION_TIMEOUT

    while time.monotonic() < deadline:
        message = await Chats.get_message_by_id_and_message_id(chat_id, message_id)
        if message:
            error = message.get('error')
            if error:
                if isinstance(error, dict):
                    error = error.get('content') or error.get('message') or str(error)
                raise RuntimeError(f'Automation assistant failed: {error}')

            if message.get('done'):
                if not _has_final_assistant_message(message):
                    raise RuntimeError('Automation completed without a final assistant message')
                return message

        await asyncio.sleep(0.5)

    raise TimeoutError(f'Automation did not complete within {AUTOMATION_COMPLETION_TIMEOUT} seconds')


async def _resolve_model_features(app, model_id: str) -> dict:
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

    capabilities = meta.get('capabilities') or {}
    features = {}

    # code_interpreter is excluded: it requires the frontend event emitter
    # and does not work in headless backend execution.
    feature_checks = {
        'web_search': await Config.get('web.search.enable'),
        'image_generation': await Config.get('image_generation.enable'),
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

    base_url = get_terminal_server_url(connection)
    if not base_url:
        return

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
    chat_id = None
    try:
        user = await Users.get_user_by_id(automation.user_id)
        if not user:
            await _record_run(automation.id, 'error', error='User not found')
            await publish_event(
                app,
                EVENTS.AUTOMATION_RUN_FAILED,
                subject_id=automation.id,
                data={'name': automation.name, 'error': 'User not found'},
            )
            return

        # Re-gate the rehydrated owner: a demoted/deactivated or de-permissioned owner must not run.
        from open_webui.utils.access_control import has_permission

        if user.role not in ('user', 'admin') or (
            user.role != 'admin'
            and not await has_permission(user.id, 'features.automations', await Config.get('user.permissions'))
        ):
            error = 'Owner no longer permitted to run automations'
            await _record_run(automation.id, 'error', error=error)
            await publish_event(
                app,
                EVENTS.AUTOMATION_RUN_FAILED,
                actor=user,
                subject_id=automation.id,
                data={'name': automation.name, 'error': error},
            )
            return

        prompt = await prompt_template(automation.data['prompt'], user)
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
            error = 'Failed to create chat'
            await _record_run(automation.id, 'error', error=error)
            await publish_event(
                app,
                EVENTS.AUTOMATION_RUN_FAILED,
                actor=user,
                subject_id=automation.id,
                data={'name': automation.name, 'error': error},
            )
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
        features = await _resolve_model_features(app, model_id)
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
        try:
            expires_delta = parse_duration(str(await Config.get('automations.auth_token_expires_in', '1h')))
        except ValueError:
            expires_delta = None
        token = create_token(
            data={'id': user.id, 'typ': 'automation'},
            expires_delta=expires_delta or timedelta(hours=1),
        )
        request = _build_request(app, token=token)
        await app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)
        await _wait_for_automation_completion(chat.id, assistant_msg_id)

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
        await publish_event(
            app,
            EVENTS.AUTOMATION_RUN_COMPLETED,
            actor=user,
            subject_id=automation.id,
            data={'name': automation.name, 'chat_id': chat.id},
        )

    except Exception as e:
        log.exception(f'Automation {automation.id} failed')
        error = str(e)[:4000]
        await _record_run(automation.id, 'error', chat_id=chat_id, error=error)
        await publish_event(
            app,
            EVENTS.AUTOMATION_RUN_FAILED,
            subject_id=automation.id,
            data={'name': automation.name, 'error': error},
        )


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
    # Grace window covers one poll cycle + jitter so "At time of event"
    # alerts (alert_minutes=0) are not missed.
    grace_ns = (SCHEDULER_POLL_INTERVAL + 5) * 1_000_000_000

    async with get_async_db() as db:
        upcoming = await CalendarEvents.get_upcoming_events(now_ns, default_lookahead_ns, grace_ns=grace_ns, db=db)

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

        # Send target notification if user has one configured
        try:
            time_str = f'in {minutes_until} min' if minutes_until > 0 else 'now'
            await publish_event(
                app,
                EVENTS.CALENDAR_ALERT,
                subject_id=event.id,
                subject_type='calendar.event',
                source='scheduler',
                data={
                    **alert_data,
                    'user_id': event.user_id,
                    'starts_in': time_str,
                    'message': f'{event.title}: starting {time_str}',
                },
                message=event.title,
            )
        except Exception:
            log.debug(f'Failed to send notification for calendar alert {event.id}', exc_info=True)


async def _record_run(
    automation_id: str,
    status: str,
    chat_id: str = None,
    error: str = None,
):
    """Insert a run record into automation_run."""
    async with get_async_db() as db:
        await AutomationRuns.insert(automation_id, status, chat_id=chat_id, error=error, db=db)
