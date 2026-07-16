from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from open_webui.events import EVENT_DEFINITIONS_BY_NAME, NOTIFICATION_EVENTS
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.retrieval.web.utils import validate_url
from open_webui.utils.webhook import post_webhook


VALID_EVENTS = set(NOTIFICATION_EVENTS)
LEGACY_EVENTS = {'chat.finished', 'chat.failed'}
VALID_DELIVERY = {'away', 'always'}
CHANNEL_MESSAGE_EVENT = 'channel.message'

DEFAULT_TARGET_ID = 'webhook'
log = logging.getLogger(__name__)


def _normalize_target(target: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = int(time.time())

    target_type = str(target.get('type') or existing.get('type') or 'webhook').strip()
    if target_type != 'webhook':
        raise ValueError('Unsupported notification target type')

    config = dict(existing.get('config') or {})
    config.update(target.get('config') or {})
    url = str(config.get('url') or '').strip()
    if not url:
        raise ValueError('Webhook URL is required')
    if '...' in url:
        url = str((existing.get('config') or {}).get('url') or '').strip()
    validate_url(url)
    config['url'] = url

    target_id = str(target.get('id') or existing.get('id') or '').strip()
    if not target_id:
        hostname = urlparse(url).hostname or 'webhook'
        target_id = re.sub(r'[^a-zA-Z0-9_-]+', '-', hostname).strip('-').lower() or 'target'

    events = target['events'] if 'events' in target else existing.get('events', [])
    if events is None:
        events = []
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    cleaned_events = []
    for event in events:
        event = str(event)
        if event not in VALID_EVENTS:
            raise ValueError(f'unsupported notification event: {event}')
        if event not in cleaned_events:
            cleaned_events.append(event)

    delivery = str(target.get('delivery') or existing.get('delivery') or 'away').strip()
    if delivery not in VALID_DELIVERY:
        raise ValueError('Invalid notification delivery mode')

    return {
        'id': target_id,
        'type': target_type,
        'enabled': bool(target.get('enabled', existing.get('enabled', True))),
        'events': cleaned_events,
        'delivery': delivery,
        'config': config,
        'created_at': int(existing.get('created_at') or now),
        'updated_at': now,
    }


def _public_target(target: dict[str, Any], default_target_id: str | None = None) -> dict[str, Any]:
    config = dict(target.get('config') or {})
    url = str(config.pop('url', '') or '')
    if url:
        parsed = urlparse(url)
        if parsed.hostname:
            path = parsed.path or ''
            suffix = path[-4:] if len(path) > 4 else path
            config['url_masked'] = f'{parsed.scheme}://{parsed.hostname}/...{suffix}'
        else:
            config['url_masked'] = '****'
    else:
        config['url_masked'] = ''
    return {**target, 'config': config, 'is_default': target.get('id') == default_target_id}


async def _load_notifications(user_id: str) -> dict[str, Any]:
    user = await Users.get_user_by_id(user_id)
    if not user:
        raise ValueError('User not found')

    settings = getattr(user, 'settings', None)
    settings = settings.model_dump(exclude_none=True) if hasattr(settings, 'model_dump') else dict(settings or {})
    notifications = dict(settings.get('notifications') or {})
    targets = notifications.get('targets')

    legacy_url = str(
        notifications.get('webhook_url') or settings.get('ui', {}).get('notifications', {}).get('webhook_url') or ''
    ).strip()

    if not isinstance(targets, list) or not targets:
        if legacy_url:
            target = _normalize_target(
                {
                    'id': DEFAULT_TARGET_ID,
                    'type': 'webhook',
                    'enabled': True,
                    'events': sorted(VALID_EVENTS),
                    'delivery': 'away',
                    'config': {'url': legacy_url},
                }
            )
            notifications = {
                **notifications,
                'targets': [target],
                'default_target_id': DEFAULT_TARGET_ID,
                'legacy_notification_events_migrated': True,
            }
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    else:
        notifications['targets'] = [target for target in targets if isinstance(target, dict)]
        notifications.setdefault(
            'default_target_id', notifications['targets'][0].get('id') if notifications['targets'] else None
        )
        if legacy_url and not notifications.get('legacy_notification_events_migrated'):
            changed = False
            for target in notifications['targets']:
                if (
                    target.get('id') == DEFAULT_TARGET_ID
                    and str((target.get('config') or {}).get('url') or '').strip() == legacy_url
                    and set(target.get('events') or []) == LEGACY_EVENTS
                ):
                    target['events'] = sorted(VALID_EVENTS)
                    changed = True
            notifications['legacy_notification_events_migrated'] = True
            if changed:
                await Users.update_user_settings_by_id(user_id, {'notifications': notifications})

    return notifications


async def list_targets(user_id: str) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    default_target_id = notifications.get('default_target_id')
    return {
        'targets': [_public_target(target, default_target_id) for target in notifications.get('targets') or []],
    }


async def create_target(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    has_explicit_id = bool(str(payload.get('id') or '').strip())
    target = _normalize_target(payload)
    if any(str(existing.get('id', '')).lower() == target['id'].lower() for existing in targets):
        if has_explicit_id:
            raise ValueError('notification target id already exists')
        base = target['id']
        suffix = 2
        while any(str(existing.get('id', '')).lower() == target['id'].lower() for existing in targets):
            target['id'] = f'{base}-{suffix}'
            suffix += 1
    targets.append(target)
    notifications['targets'] = targets
    notifications.setdefault('default_target_id', target['id'])
    await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    return _public_target(target, notifications.get('default_target_id'))


async def update_target(user_id: str, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    for index, existing in enumerate(targets):
        if str(existing.get('id', '')).lower() == target_id.lower():
            updated = _normalize_target({'id': target_id, **payload}, existing=existing)
            if any(
                idx != index and str(target.get('id', '')).lower() == updated['id'].lower()
                for idx, target in enumerate(targets)
            ):
                raise ValueError('notification target id already exists')
            targets[index] = updated
            notifications['targets'] = targets
            if str(notifications.get('default_target_id') or '').lower() == target_id.lower():
                notifications['default_target_id'] = updated['id']
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
            return _public_target(updated, notifications.get('default_target_id'))
    raise ValueError('Notification target not found')


async def delete_target(user_id: str, target_id: str) -> bool:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    next_targets = [target for target in targets if str(target.get('id', '')).lower() != target_id.lower()]
    if len(next_targets) == len(targets):
        return False
    notifications['targets'] = next_targets
    if str(notifications.get('default_target_id') or '').lower() == target_id.lower():
        notifications['default_target_id'] = next_targets[0].get('id') if next_targets else None
    await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    return True


async def set_default_target(user_id: str, target_id: str) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    for target in notifications.get('targets') or []:
        if str(target.get('id', '')).lower() == target_id.lower():
            notifications['default_target_id'] = target['id']
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
            return _public_target(target, target['id'])
    raise ValueError('Notification target not found')


def get_notification_event_catalog() -> list[dict[str, str]]:
    return [
        {
            'event': event_name,
            'label': EVENT_DEFINITIONS_BY_NAME[event_name].message or event_name,
            'description': EVENT_DEFINITIONS_BY_NAME[event_name].description or '',
        }
        for event_name in NOTIFICATION_EVENTS
    ]


def _find_target(notifications: dict[str, Any], target: str = '') -> dict[str, Any] | None:
    targets = notifications.get('targets') or []
    target = target.strip()
    target_id = target or str(notifications.get('default_target_id') or '')
    if not target_id:
        return None
    for item in targets:
        if str(item.get('id', '')).lower() == target_id.lower():
            return item
    return None


async def _send_webhook(app_name: str, target: dict[str, Any], message: str, data: dict[str, Any], title: str = ''):
    url = str((target.get('config') or {}).get('url') or '').strip()
    if not url:
        raise ValueError('Webhook URL is required')
    ok = await post_webhook(app_name, url, title or message, data, description=message if title else None)
    if not ok:
        raise ValueError('Webhook delivery failed')


async def test_target(user_id: str, target_id: str, app_name: str = 'Open WebUI') -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    target = _find_target(notifications, target_id)
    if not target:
        raise ValueError('Notification target not found')
    await _send_webhook(
        app_name,
        target,
        'This is a test notification from Open WebUI.',
        {'event': 'notification.test', 'action': 'test', 'user_id': user_id},
        'Test notification',
    )
    return {'ok': True}


async def notify_target(
    user_id: str, message: str, target: str = '', title: str = '', app_name: str = 'Open WebUI'
) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    item = _find_target(notifications, target)
    if not item:
        raise ValueError('Notification target not found')
    if not item.get('enabled', True):
        raise ValueError('Notification target is disabled')
    await _send_webhook(
        app_name,
        item,
        message,
        {'event': 'notification.manual', 'action': 'notify', 'user_id': user_id, 'message': message, 'title': title},
        title or 'Notification',
    )
    return {'ok': True, 'target_id': item.get('id')}


async def dispatch_notification_event(app: Any, event: Any) -> None:
    if event.event not in VALID_EVENTS or not await Config.get('ui.enable_user_webhooks'):
        return

    from open_webui.events import event_user_ids

    app_name = getattr(getattr(app, 'state', None), 'WEBUI_NAME', 'Open WebUI')
    for user_id in event_user_ids(event):
        try:
            notifications = await _load_notifications(user_id)
            is_active = False if event.event == CHANNEL_MESSAGE_EVENT else await Users.is_user_active(user_id)

            for target in notifications.get('targets') or []:
                if not target.get('enabled', True):
                    continue
                if event.event not in target.get('events', []):
                    continue
                if target.get('delivery', 'away') == 'away' and is_active:
                    continue

                data = event.model_dump()
                definition = EVENT_DEFINITIONS_BY_NAME.get(event.event)
                title = event.message or (definition.message if definition else event.event)
                message = str(
                    (event.data or {}).get('message')
                    or (event.data or {}).get('preview')
                    or (event.data or {}).get('content_preview')
                    or title
                )
                await _send_webhook(app_name, target, message, data, title)
        except Exception:
            log.exception('Notification delivery failed for user %s and event %s', user_id, event.event)
