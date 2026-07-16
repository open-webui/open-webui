from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.retrieval.web.utils import validate_url
from open_webui.utils.webhook import post_webhook


VALID_EVENTS = {'chat.finished', 'chat.failed'}
VALID_DELIVERY = {'away', 'always'}

DEFAULT_TARGET_ID = 'webhook'
log = logging.getLogger(__name__)


def _normalize_target(target: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = int(time.time())

    target_type = str(target.get('type') or existing.get('type') or 'webhook').strip()
    if target_type != 'webhook':
        raise ValueError('Unsupported notification target type')

    name = str(target.get('name') or existing.get('name') or 'Webhook').strip() or 'Webhook'
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in name).strip('-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    target_id = str(target.get('id') or existing.get('id') or slug[:48] or uuid.uuid4().hex[:8]).strip()

    config = dict(existing.get('config') or {})
    config.update(target.get('config') or {})
    url = str(config.get('url') or '').strip()
    if not url:
        raise ValueError('Webhook URL is required')
    if '...' in url:
        url = str((existing.get('config') or {}).get('url') or '').strip()
    validate_url(url)
    config['url'] = url

    events = target['events'] if 'events' in target else existing.get('events', [])
    if events is None:
        events = []
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    events = [str(event) for event in events]
    unsupported = [event for event in events if event not in VALID_EVENTS]
    if unsupported:
        raise ValueError(f'unsupported notification event: {unsupported[0]}')

    delivery = str(target.get('delivery') or existing.get('delivery') or 'away')
    if delivery not in VALID_DELIVERY:
        raise ValueError('Invalid notification delivery mode')

    return {
        'id': target_id,
        'type': target_type,
        'name': name,
        'enabled': bool(target.get('enabled', existing.get('enabled', True))),
        'events': events,
        'delivery': delivery,
        'config': config,
        'created_at': int(existing.get('created_at') or now),
        'updated_at': now,
    }


def _public_target(target: dict[str, Any]) -> dict[str, Any]:
    config = dict(target.get('config') or {})
    if config.get('url'):
        url = str(config['url'])
        config['url'] = '********' if len(url) <= 12 else f'{url[:8]}...{url[-4:]}'
    return {**target, 'config': config}


async def _load_notifications(user_id: str) -> dict[str, Any]:
    user = await Users.get_user_by_id(user_id)
    if not user:
        raise ValueError('User not found')

    settings = getattr(user, 'settings', None)
    settings = settings.model_dump(exclude_none=True) if hasattr(settings, 'model_dump') else dict(settings or {})
    notifications = dict(settings.get('notifications') or {})
    targets = notifications.get('targets')

    if not isinstance(targets, list) or not targets:
        legacy_url = str(
            notifications.get('webhook_url')
            or settings.get('ui', {}).get('notifications', {}).get('webhook_url')
            or ''
        ).strip()
        if legacy_url:
            target = _normalize_target(
                {
                    'id': DEFAULT_TARGET_ID,
                    'name': 'Webhook',
                    'type': 'webhook',
                    'enabled': True,
                    'events': sorted(VALID_EVENTS),
                    'delivery': 'away',
                    'config': {'url': legacy_url},
                }
            )
            notifications = {**notifications, 'targets': [target], 'default_target_id': DEFAULT_TARGET_ID}
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    else:
        notifications['targets'] = [target for target in targets if isinstance(target, dict)]
        notifications.setdefault(
            'default_target_id', notifications['targets'][0].get('id') if notifications['targets'] else None
        )

    return notifications


async def list_targets(user_id: str) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    return {
        'targets': [_public_target(target) for target in notifications.get('targets') or []],
        'default_target_id': notifications.get('default_target_id'),
    }


async def create_target(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    target = _normalize_target(payload)
    if any(existing.get('id') == target['id'] for existing in targets):
        target['id'] = f'{target["id"]}-{uuid.uuid4().hex[:6]}'
    targets.append(target)
    notifications['targets'] = targets
    notifications.setdefault('default_target_id', target['id'])
    await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    return _public_target(target)


async def update_target(user_id: str, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    for index, existing in enumerate(targets):
        if existing.get('id') == target_id:
            updated = _normalize_target({'id': target_id, **payload}, existing=existing)
            targets[index] = updated
            notifications['targets'] = targets
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
            return _public_target(updated)
    raise ValueError('Notification target not found')


async def delete_target(user_id: str, target_id: str) -> bool:
    notifications = await _load_notifications(user_id)
    targets = notifications.get('targets') or []
    next_targets = [target for target in targets if target.get('id') != target_id]
    if len(next_targets) == len(targets):
        return False
    notifications['targets'] = next_targets
    if notifications.get('default_target_id') == target_id:
        notifications['default_target_id'] = next_targets[0].get('id') if next_targets else None
    await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    return True


async def set_default_target(user_id: str, target_id: str) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    if not any(target.get('id') == target_id for target in notifications.get('targets') or []):
        raise ValueError('Notification target not found')
    notifications['default_target_id'] = target_id
    await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
    return await list_targets(user_id)


def _find_target(notifications: dict[str, Any], target: str = '') -> dict[str, Any] | None:
    targets = notifications.get('targets') or []
    target = target.strip()
    target_id = target or str(notifications.get('default_target_id') or '')
    for item in targets:
        if item.get('id') == target_id or item.get('name') == target:
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
            is_active = await Users.is_user_active(user_id)

            for target in notifications.get('targets') or []:
                if not target.get('enabled', True):
                    continue
                if event.event not in target.get('events', []):
                    continue
                if target.get('delivery', 'away') == 'away' and is_active:
                    continue

                data = event.model_dump()
                title = event.message or data.get('message') or event.event
                message = str((event.data or {}).get('message') or title)
                await _send_webhook(app_name, target, message, data, title)
        except Exception:
            log.exception('Notification delivery failed for user %s and event %s', user_id, event.event)
