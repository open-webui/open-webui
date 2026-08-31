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

from dateutil.rrule import HOURLY, MINUTELY, SECONDLY, rruleset, rrulestr
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db
from open_webui.models.automations import AutomationModel, AutomationRuns, Automations
from open_webui.models.chats import ChatForm, Chats
from open_webui.models.config import Config
from open_webui.models.folders import Folders
from open_webui.models.messages import MessageForm
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

    SECONDLY/MINUTELY/HOURLY rules use a fixed epoch DTSTART (2000-01-01 00:00)
    so intervals snap to clock boundaries (e.g. every 5min = :00, :05, :10).
    """
    upper = s.upper()
    if 'EXRULE' in upper:
        raise ValueError('EXRULE is not supported in recurrence rules')

    parsed = rrulestr(s, ignoretz=True)
    rules = parsed._rrule if isinstance(parsed, rruleset) else [parsed]
    if len(rules) > 1:
        raise ValueError('only one RRULE is supported per recurrence rule')

    rule = rules[0]
    start = rule._dtstart.replace(tzinfo=None)
    anchor = now or datetime.now()
    lines = s.splitlines()
    stripped = '\n'.join(line for line in lines if not line.upper().startswith('DTSTART')) or s
    has_dtstart = any(line.upper().startswith('DTSTART') for line in lines)
    step = {
        SECONDLY: timedelta(seconds=rule._interval),
        MINUTELY: timedelta(minutes=rule._interval),
        HOURLY: timedelta(hours=rule._interval),
    }.get(rule._freq)

    if step is None:
        if not rule._dtstart.tzinfo:
            return parsed
        return rrulestr(stripped, dtstart=start, ignoretz=True)

    if rule._interval < 1:
        raise ValueError('RRULE INTERVAL must be a positive integer')
    dtstart = None
    if has_dtstart:
        emitted = ((anchor - start) // step) if anchor > start else 0
        emitted *= len(rule._byminute or (0,)) * len(rule._bysecond or (0,))
        if emitted <= 100_000:
            if rule._dtstart.tzinfo:
                dtstart = start
            else:
                return parsed
    if not has_dtstart or dtstart is None:
        epoch = datetime(2000, 1, 1)
        dtstart = epoch + ((anchor - epoch) // step) * step

    return rrulestr(stripped, dtstart=dtstart, ignoretz=True)


def validate_rrule(s: str, tz: str = None) -> None:
    """Raise ValueError if the RRULE is malformed or exhausted.

    When *tz* is provided the "now" reference uses the user's local
    clock so that near-future schedules are not incorrectly rejected
    on servers whose system clock is ahead (e.g. UTC vs US timezones).
    """
    upper = s.upper()
    if 'COUNT=' in upper and 'DTSTART' not in upper:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_COUNT_REQUIRES_DTSTART)
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
    s = '\n'.join(line for line in s.splitlines() if not line.upper().startswith('DTSTART')) or s
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
        'Scheduler worker started (timer poll interval: %ss, scheduler poll interval: %ss)',
        TIMER_POLL_INTERVAL,
        SCHEDULER_POLL_INTERVAL,
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
                        log.info('Claimed %s due automation(s)', len(batch))
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


async def _resolve_model_defaults(app, model_id: str) -> tuple[list[str], dict, list[str], Optional[str]]:
    models = getattr(app.state, 'MODELS', {})
    model = models.get(model_id, {})
    meta = model.get('info', {}).get('meta', {})

    tool_ids = list(meta.get('toolIds') or [])
    filter_ids = list(meta.get('defaultFilterIds') or [])
    terminal_id = meta.get('terminalId') or None
    default_feature_ids = meta.get('defaultFeatureIds', [])
    if not default_feature_ids:
        return tool_ids, {}, filter_ids, terminal_id

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

    return tool_ids, features, filter_ids, terminal_id


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


async def _execute_channel_automation(
    app,
    automation: AutomationModel,
    user,
    prompt: str,
    model_id: str,
    token: str,
) -> None:
    target = automation.data.get('target') or {}
    channel_id = target.get('channel_id')
    if not channel_id or not await Config.get('channels.enable'):
        raise ValueError('Channel not found')

    model = getattr(app.state, 'MODELS', {}).get(model_id, {})
    request = _build_request(app, token=token)

    from open_webui.routers.channels import new_message_handler

    async with get_async_db() as db:
        user_message, channel = await new_message_handler(
            request,
            channel_id,
            MessageForm(
                content=prompt,
                data={},
                meta={'automation_id': automation.id},
            ),
            user,
            db,
        )
        response_parent_id = (
            user_message.parent_id
            if user_message.parent_id
            else (user_message.id if await Config.get('channels.model_response_mode', 'thread') == 'thread' else None)
        )
        assistant_message, channel = await new_message_handler(
            request,
            channel.id,
            MessageForm(
                parent_id=response_parent_id,
                content='',
                data={},
                meta={
                    'automation_id': automation.id,
                    'model_id': model_id,
                    'model_name': model.get('name', model_id),
                },
            ),
            user,
            db,
        )

    tool_ids, features, filter_ids, _ = await _resolve_model_defaults(app, model_id)

    form_data = {
        'model': model_id,
        'messages': [
            {
                'role': 'system',
                'content': f'You are {model.get("name", model_id)}, participating in a channel conversation. Be concise and conversational.',
            },
            {'role': 'user', 'content': f'{user.name if user else "User"}: {prompt}'},
        ],
        'stream': True,
        'chat_id': f'channel:{channel.id}',
        'id': assistant_message.id,
        'session_id': f'channel:{channel.id}',
        'automation_id': automation.id,
        'background_tasks': {},
    }
    if tool_ids:
        form_data['tool_ids'] = tool_ids
    if features:
        form_data['features'] = features
    if filter_ids:
        form_data['filter_ids'] = filter_ids

    await app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)

    from open_webui.socket.main import sio

    await sio.emit(
        'automation:result',
        {
            'automation_id': automation.id,
            'name': automation.name,
            'chat_id': f'channel:{channel.id}',
            'message_id': assistant_message.id,
            'status': 'success',
        },
        room=f'user:{automation.user_id}',
    )

    await _record_run(automation.id, 'success', chat_id=f'channel:{channel.id}')
    await publish_event(
        app,
        EVENTS.AUTOMATION_RUN_COMPLETED,
        actor=user,
        subject_id=automation.id,
        data={'name': automation.name, 'channel_id': channel.id, 'message_id': assistant_message.id},
    )


async def execute_automation(app, automation: AutomationModel) -> None:
    """Execute an automation through the full chat completion pipeline.

    Creates a real chat or channel message, then calls chat_completion exactly like the frontend:
    session_id + chat_id + message_id → async task → pipeline handles everything
    (filters, model params, knowledge/RAG, tools, DB saves, webhooks).
    """
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
        try:
            expires_delta = parse_duration(str(await Config.get('automations.auth_token_expires_in', '1h')))
        except ValueError:
            expires_delta = None
        token = create_token(
            data={'id': user.id, 'typ': 'automation'},
            expires_delta=expires_delta or timedelta(hours=1),
        )

        target = automation.data.get('target') or {}
        if target.get('type') == 'channel':
            await _execute_channel_automation(app, automation, user, prompt, model_id, token)
            return

        folder_id = automation.folder_id
        if folder_id and not await Folders.get_folder_by_id_and_user_id(folder_id, automation.user_id):
            await Automations.clear_folder_ids(automation.user_id, [folder_id])
            folder_id = None

        # Generate proper UUIDs for messages (same as frontend)
        user_msg_id = str(uuid4())
        assistant_msg_id = str(uuid4())

        chat_id = str(uuid4())
        chat = await Chats.insert_new_chat(
            chat_id,
            automation.user_id,
            ChatForm(
                folder_id=folder_id,
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
                },
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
        tool_ids, features, filter_ids, terminal_id = await _resolve_model_defaults(app, model_id)

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
            'automation_id': automation.id,
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
        request = _build_request(app, token=token)
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
        await _record_run(automation.id, 'error', error=error)
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
            log.debug('Failed to mark event %s as alerted', event.id, exc_info=True)

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
            log.debug('Failed to send notification for calendar alert %s', event.id, exc_info=True)


async def _record_run(
    automation_id: str,
    status: str,
    chat_id: str = None,
    error: str = None,
):
    """Insert a run record into automation_run."""
    async with get_async_db() as db:
        await AutomationRuns.insert(automation_id, status, chat_id=chat_id, error=error, db=db)
