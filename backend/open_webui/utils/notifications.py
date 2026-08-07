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
from open_webui.utils.webpush import WebPushSubscriptionGone, send_web_push


VALID_EVENTS = set(NOTIFICATION_EVENTS)
LEGACY_EVENTS = {'chat.finished', 'chat.failed'}
VALID_DELIVERY = {'away', 'always'}
CHAT_FINISHED_EVENT = 'chat.finished'
CHAT_FAILED_EVENT = 'chat.failed'
CHANNEL_MESSAGE_EVENT = 'channel.message'
CALENDAR_ALERT_EVENT = 'calendar.alert'

DEFAULT_TARGET_ID = 'webhook'
MAX_WEBPUSH_TARGETS = 10
DESCRIPTION_DEFAULT = object()
log = logging.getLogger(__name__)


def _normalize_target(target: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = int(time.time())

    target_type = str(target.get('type') or existing.get('type') or 'webhook').strip()
    if target_type not in ('webhook', 'webpush'):
        raise ValueError('Unsupported notification target type')
    if existing and target.get('type') and str(existing.get('type') or 'webhook') != target_type:
        raise ValueError('Notification target type cannot be changed')

    if target_type == 'webhook':
        config = dict(existing.get('config') or {})
        config.update(target.get('config') or {})
        url = str(config.get('url') or '').strip()
        if not url:
            raise ValueError('Webhook URL is required')
        if '...' in url:
            url = str((existing.get('config') or {}).get('url') or '').strip()
        validate_url(url)
        config['url'] = url
        default_id_source = urlparse(url).hostname or 'webhook'
    elif existing:
        # Only events/delivery/enabled are editable; the subscription itself is immutable
        if target.get('config'):
            raise ValueError('Push subscription cannot be edited')
        config = dict(existing.get('config') or {})
        default_id_source = f'push-{urlparse(str(config.get("endpoint") or "")).hostname or "device"}'
    else:
        config = dict(target.get('config') or {})
        endpoint = str(config.get('endpoint') or '').strip()
        if not endpoint.startswith('https://'):
            raise ValueError('Push subscription endpoint must be an https URL')
        validate_url(endpoint)
        keys = config.get('keys')
        if not (isinstance(keys, dict) and keys.get('p256dh') and keys.get('auth')):
            raise ValueError('Push subscription keys are required')
        config = {'endpoint': endpoint, 'keys': {'p256dh': keys['p256dh'], 'auth': keys['auth']}}
        default_id_source = f'push-{urlparse(endpoint).hostname or "device"}'

    target_id = str(target.get('id') or existing.get('id') or '').strip()
    if not target_id:
        target_id = re.sub(r'[^a-zA-Z0-9_-]+', '-', default_id_source).strip('-').lower() or 'target'

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
    if target.get('type') == 'webpush':
        endpoint = str(config.pop('endpoint', '') or '')
        config.pop('keys', None)
        hostname = urlparse(endpoint).hostname if endpoint else None
        config['url_masked'] = f'push://{hostname}' if hostname else ''
    else:
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
    if not notifications.get('default_target_id'):
        notifications['default_target_id'] = target['id']
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


async def upsert_webpush_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> dict[str, Any]:
    if not (p256dh and auth):
        raise ValueError('Push subscription keys are required')
    notifications = await _load_notifications(user_id)
    webpush_targets = [t for t in notifications.get('targets') or [] if t.get('type') == 'webpush']
    keys = {'p256dh': p256dh, 'auth': auth}
    for existing in webpush_targets:
        if (existing.get('config') or {}).get('endpoint') == endpoint:
            if (existing.get('config') or {}).get('keys') == keys:
                # User toggled push back on for this device
                return await update_target(user_id, str(existing.get('id') or ''), {'enabled': True})
            # Rotated keys: swap the subscription in place, keeping id, events,
            # delivery and the default marker
            existing['config'] = {'endpoint': endpoint, 'keys': keys}
            existing['enabled'] = True
            existing['updated_at'] = int(time.time())
            await Users.update_user_settings_by_id(user_id, {'notifications': notifications})
            return _public_target(existing, notifications.get('default_target_id'))
    if len(webpush_targets) >= MAX_WEBPUSH_TARGETS:
        # Evict the least-recently-updated subscription to make room
        stalest = min(webpush_targets, key=lambda t: int(t.get('updated_at') or t.get('created_at') or 0))
        await delete_target(user_id, str(stalest.get('id') or ''))
    return await create_target(
        user_id,
        {
            'type': 'webpush',
            'enabled': True,
            'events': sorted(VALID_EVENTS),
            'delivery': 'away',
            'config': {'endpoint': endpoint, 'keys': keys},
        },
    )


async def list_webpush_endpoints(user_id: str) -> list[str]:
    notifications = await _load_notifications(user_id)
    return [
        str((target.get('config') or {}).get('endpoint') or '')
        for target in notifications.get('targets') or []
        if target.get('type') == 'webpush' and target.get('enabled', True)
    ]


async def delete_webpush_subscription(user_id: str, endpoint: str) -> bool:
    notifications = await _load_notifications(user_id)
    for target in notifications.get('targets') or []:
        if target.get('type') == 'webpush' and (target.get('config') or {}).get('endpoint') == endpoint:
            return await delete_target(user_id, str(target.get('id') or ''))
    return False


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


async def _send_target(
    app_name: str,
    target: dict[str, Any],
    message: str,
    data: dict[str, Any],
    title: str = '',
    description: str | None | object = DESCRIPTION_DEFAULT,
):
    config = target.get('config') or {}

    if target.get('type') == 'webpush':
        if not await Config.get('webpush.enable'):
            raise ValueError('Web push is disabled')
        body = str(data.get('message') or message).replace('**', '').strip()
        push_title = title.replace('**', '').strip() or str(data.get('title') or app_name)
        if push_title and body.startswith(push_title):
            body = body[len(push_title) :].lstrip('\n ')
        # Push payloads are capped at ~4KB after encryption
        payload = {
            'title': push_title[:200],
            'body': body[:500],
            'url': str(data.get('app_url') or data.get('url') or ''),
        }
        await send_web_push({'endpoint': config.get('endpoint'), 'keys': config.get('keys') or {}}, payload)
        return

    # app_url is internal routing data, not part of the webhook payload contract
    data = {key: value for key, value in data.items() if key != 'app_url'}
    url = str(config.get('url') or '').strip()
    if not url:
        raise ValueError('Webhook URL is required')
    if description is DESCRIPTION_DEFAULT:
        description = message if title else None
    ok = await post_webhook(app_name, url, title or message, data, description=description)
    if not ok:
        raise ValueError('Webhook delivery failed')


def _notification_webhook_content(event: Any) -> tuple[str, str, dict[str, Any], str | None]:
    data = event.data or {}

    if event.event == CHAT_FINISHED_EVENT:
        title = str(data.get('title') or event.message or 'Chat finished')
        content = str(data.get('message') or '')
        url = str(data.get('url') or '')
        app_url = url
        chat_id = str(data.get('chat_id') or '')
        if chat_id and url.endswith(f'/c/{chat_id}'):
            url = f'{url[: -len(f"/c/{chat_id}")].rstrip("/")}/{chat_id}'
        body = '\n'.join(part for part in (content, url) if part)
        return (
            f'**{title}**',
            body,
            {
                'action': 'chat',
                'message': content,
                'title': title,
                'url': url,
                'app_url': app_url,
            },
            body,
        )

    if event.event == CHAT_FAILED_EVENT:
        title = str(event.message or 'Chat failed')
        content = str(data.get('message') or '')
        url = str(data.get('url') or '')
        app_url = url
        chat_id = str(data.get('chat_id') or '')
        if chat_id and url.endswith(f'/c/{chat_id}'):
            url = f'{url[: -len(f"/c/{chat_id}")].rstrip("/")}/{chat_id}'
        body = '\n'.join(part for part in (content, url) if part)
        return (
            f'**{title}**',
            body,
            {
                'action': 'chat_failed',
                'message': content,
                'title': title,
                'url': url,
                'app_url': app_url,
            },
            body,
        )

    if event.event == CHANNEL_MESSAGE_EVENT:
        channel_name = str(data.get('title') or event.message or 'Channel')
        content = str(data.get('content') or data.get('message') or '')
        url = str(data.get('url') or '')
        body = '\n'.join(part for part in (content, url) if part)
        return (
            f'**#{channel_name}**',
            body,
            {
                'action': 'channel',
                'message': content,
                'title': channel_name,
                'url': url,
            },
            body,
        )

    if event.event == CALENDAR_ALERT_EVENT:
        title = str(data.get('title') or event.message or 'Calendar alert')
        starts_in = str(data.get('starts_in') or '')
        message = f'**{title}**\nstarting {starts_in}'.strip()
        return (
            '',
            message,
            {
                'action': 'calendar_alert',
                'title': title,
                'minutes_until': data.get('minutes_until'),
                'event_id': data.get('event_id') or (event.subject or {}).get('id'),
            },
            None,
        )

    definition = EVENT_DEFINITIONS_BY_NAME.get(event.event)
    title = event.message or (definition.message if definition else event.event)
    message = str(data.get('message') or data.get('preview') or data.get('content_preview') or title)
    return str(title), message, event.model_dump(), message if title else None


# LICENSE covers this Open WebUI notification identifier.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
async def test_target(user_id: str, target_id: str, app_name: str = 'Open WebUI') -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    target = _find_target(notifications, target_id)
    if not target:
        raise ValueError('Notification target not found')
    try:
        await _send_target(
            app_name,
            target,
            # LICENSE covers this Open WebUI notification copy.
            # Do not alter, remove, obscure, or replace it except as LICENSE permits:
            # https://docs.openwebui.com/license.
            'This is a test notification from Open WebUI.',
            {'action': 'test', 'user_id': user_id},
            'Test notification',
        )
    except WebPushSubscriptionGone:
        await delete_target(user_id, str(target.get('id') or ''))
        raise ValueError('Push subscription expired')
    return {'ok': True}


# LICENSE covers this Open WebUI notification identifier.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
async def notify_target(
    user_id: str,
    message: str,
    target: str = '',
    title: str = '',
    app_name: str = 'Open WebUI',
) -> dict[str, Any]:
    notifications = await _load_notifications(user_id)
    item = _find_target(notifications, target)
    if not item:
        raise ValueError('Notification target not found')
    if not item.get('enabled', True):
        raise ValueError('Notification target is disabled')
    try:
        await _send_target(
            app_name,
            item,
            message,
            {'action': 'notify', 'user_id': user_id, 'message': message, 'title': title},
            title or 'Notification',
        )
    except WebPushSubscriptionGone:
        await delete_target(user_id, str(item.get('id') or ''))
        raise ValueError('Push subscription expired')
    return {'ok': True, 'target_id': item.get('id')}


async def dispatch_notification_event(app: Any, event: Any) -> None:
    if event.event not in VALID_EVENTS:
        return
    webhooks_enabled = await Config.get('ui.enable_user_webhooks')
    webpush_enabled = await Config.get('webpush.enable')
    if not (webhooks_enabled or webpush_enabled):
        return

    from open_webui.events import event_user_ids

    # LICENSE covers this Open WebUI notification identifier.
    # Do not alter, remove, obscure, or replace it except as LICENSE permits:
    # https://docs.openwebui.com/license.
    app_name = getattr(getattr(app, 'state', None), 'WEBUI_NAME', 'Open WebUI')
    for user_id in event_user_ids(event):
        try:
            notifications = await _load_notifications(user_id)
            is_active = False if event.event == CHANNEL_MESSAGE_EVENT else await Users.is_user_active(user_id)

            for target in notifications.get('targets') or []:
                is_webpush = target.get('type') == 'webpush'
                if not (webpush_enabled if is_webpush else webhooks_enabled):
                    continue
                if not target.get('enabled', True):
                    continue
                if event.event not in target.get('events', []):
                    continue
                if target.get('delivery', 'away') == 'away' and is_active:
                    continue

                title, message, data, description = _notification_webhook_content(event)
                try:
                    await _send_target(app_name, target, message, data, title, description=description)
                except WebPushSubscriptionGone:
                    await delete_target(user_id, str(target.get('id') or ''))
                except Exception as e:
                    log.warning(
                        'Notification target %s failed for user %s and event %s: %s',
                        target.get('id'),
                        user_id,
                        event.event,
                        e,
                    )
        except Exception:
            log.exception('Notification delivery failed for user %s and event %s', user_id, event.event)
