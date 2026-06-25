from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from types import SimpleNamespace
from typing import Any

from open_webui.env import VERSION
from open_webui.models.config import Config
from open_webui.retrieval.web.utils import validate_url
from open_webui.utils.webhook import post_webhook

log = logging.getLogger(__name__)

MAX_STRING_LENGTH = 1000
EVENT_WEBHOOKS_CONFIG_KEY = 'events.webhooks'
LEGACY_WEBHOOK_CONFIG_KEY = 'webhook_url'
DEFAULT_WEBHOOK_ID = 'default'


class EVENTS(StrEnum):
    SYSTEM_STARTUP_STARTED = 'system.startup.started'
    SYSTEM_STARTUP_COMPLETED = 'system.startup.completed'
    SYSTEM_SHUTDOWN_STARTED = 'system.shutdown.started'
    SYSTEM_SHUTDOWN_COMPLETED = 'system.shutdown.completed'
    CONFIG_IMPORTED = 'config.imported'
    CONFIG_UPDATED = 'config.updated'
    CONFIG_WEBHOOK_UPDATED = 'config.webhook.updated'
    CONFIG_CONNECTIONS_UPDATED = 'config.connections.updated'
    CONFIG_TOOL_SERVERS_UPDATED = 'config.tool_servers.updated'
    CONFIG_TERMINAL_SERVERS_UPDATED = 'config.terminal_servers.updated'
    CONFIG_CODE_EXECUTION_UPDATED = 'config.code_execution.updated'
    CONFIG_MODELS_UPDATED = 'config.models.updated'
    CONFIG_BANNERS_UPDATED = 'config.banners.updated'
    CONFIG_SUGGESTIONS_UPDATED = 'config.suggestions.updated'
    AUTH_SIGNUP = 'auth.signup'
    AUTH_LOGIN = 'auth.login'
    AUTH_LOGOUT = 'auth.logout'
    AUTH_PASSWORD_CHANGED = 'auth.password_changed'
    AUTH_API_KEY_CREATED = 'auth.api_key.created'
    AUTH_API_KEY_DELETED = 'auth.api_key.deleted'
    AUTH_OAUTH_SESSION_DELETED = 'auth.oauth_session.deleted'
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_ROLE_UPDATED = 'user.role_updated'
    USER_STATUS_UPDATED = 'user.status_updated'
    USER_SETTINGS_UPDATED = 'user.settings_updated'
    USER_PROFILE_UPDATED = 'user.profile_updated'
    USER_PERMISSIONS_UPDATED = 'user.permissions_updated'
    GROUP_CREATED = 'group.created'
    GROUP_UPDATED = 'group.updated'
    GROUP_DELETED = 'group.deleted'
    GROUP_MEMBER_ADDED = 'group.member_added'
    GROUP_MEMBER_REMOVED = 'group.member_removed'
    CHAT_CREATED = 'chat.created'
    CHAT_IMPORTED = 'chat.imported'
    CHAT_UPDATED = 'chat.updated'
    CHAT_DELETED = 'chat.deleted'
    CHAT_DELETED_ALL = 'chat.deleted_all'
    CHAT_COMPACTED = 'chat.compacted'
    CHAT_PINNED = 'chat.pinned'
    CHAT_UNPINNED = 'chat.unpinned'
    CHAT_CLONED = 'chat.cloned'
    CHAT_ARCHIVED = 'chat.archived'
    CHAT_UNARCHIVED = 'chat.unarchived'
    CHAT_SHARED = 'chat.shared'
    CHAT_UNSHARED = 'chat.unshared'
    CHAT_FOLDER_UPDATED = 'chat.folder_updated'
    CHAT_TAG_ADDED = 'chat.tag_added'
    CHAT_TAG_REMOVED = 'chat.tag_removed'
    MESSAGE_CREATED = 'message.created'
    MESSAGE_UPDATED = 'message.updated'
    MESSAGE_DELETED = 'message.deleted'
    MESSAGE_EVENT_RECEIVED = 'message.event_received'
    MESSAGE_REACTION_ADDED = 'message.reaction_added'
    MESSAGE_REACTION_REMOVED = 'message.reaction_removed'
    MESSAGE_PINNED = 'message.pinned'
    MESSAGE_UNPINNED = 'message.unpinned'
    CHANNEL_CREATED = 'channel.created'
    CHANNEL_UPDATED = 'channel.updated'
    CHANNEL_DELETED = 'channel.deleted'
    CHANNEL_MEMBER_ADDED = 'channel.member_added'
    CHANNEL_MEMBER_REMOVED = 'channel.member_removed'
    CHANNEL_MEMBER_ACTIVE_UPDATED = 'channel.member_active_updated'
    CHANNEL_WEBHOOK_CREATED = 'channel.webhook.created'
    CHANNEL_WEBHOOK_UPDATED = 'channel.webhook.updated'
    CHANNEL_WEBHOOK_DELETED = 'channel.webhook.deleted'
    FILE_UPLOADED = 'file.uploaded'
    FILE_CONTENT_UPDATED = 'file.content_updated'
    FILE_RENAMED = 'file.renamed'
    FILE_DELETED = 'file.deleted'
    FILE_DELETED_ALL = 'file.deleted_all'
    FOLDER_CREATED = 'folder.created'
    FOLDER_UPDATED = 'folder.updated'
    FOLDER_PARENT_UPDATED = 'folder.parent_updated'
    FOLDER_ACCESS_UPDATED = 'folder.access_updated'
    FOLDER_DELETED = 'folder.deleted'
    NOTE_CREATED = 'note.created'
    NOTE_UPDATED = 'note.updated'
    NOTE_ACCESS_UPDATED = 'note.access_updated'
    NOTE_PINNED = 'note.pinned'
    NOTE_UNPINNED = 'note.unpinned'
    NOTE_DELETED = 'note.deleted'
    MEMORY_CREATED = 'memory.created'
    MEMORY_UPDATED = 'memory.updated'
    MEMORY_DELETED = 'memory.deleted'
    MEMORY_RESET = 'memory.reset'
    KNOWLEDGE_CREATED = 'knowledge.created'
    KNOWLEDGE_UPDATED = 'knowledge.updated'
    KNOWLEDGE_DELETED = 'knowledge.deleted'
    KNOWLEDGE_RESET = 'knowledge.reset'
    KNOWLEDGE_REINDEXED = 'knowledge.reindexed'
    KNOWLEDGE_ACCESS_UPDATED = 'knowledge.access_updated'
    KNOWLEDGE_FILE_ADDED = 'knowledge.file.added'
    KNOWLEDGE_FILE_UPDATED = 'knowledge.file.updated'
    KNOWLEDGE_FILE_REMOVED = 'knowledge.file.removed'
    KNOWLEDGE_FILE_MOVED = 'knowledge.file.moved'
    KNOWLEDGE_DIRECTORY_CREATED = 'knowledge.directory.created'
    KNOWLEDGE_DIRECTORY_UPDATED = 'knowledge.directory.updated'
    KNOWLEDGE_DIRECTORY_DELETED = 'knowledge.directory.deleted'
    KNOWLEDGE_EXTERNAL_CONNECTION_CREATED = 'knowledge.external_connection.created'
    KNOWLEDGE_EXTERNAL_CONNECTION_UPDATED = 'knowledge.external_connection.updated'
    KNOWLEDGE_EXTERNAL_CONNECTION_DELETED = 'knowledge.external_connection.deleted'
    RETRIEVAL_CONTENT_PROCESSED = 'retrieval.content.processed'
    RETRIEVAL_COLLECTION_DELETED = 'retrieval.collection.deleted'
    RETRIEVAL_VECTOR_DB_RESET = 'retrieval.vector_db.reset'
    RETRIEVAL_UPLOADS_RESET = 'retrieval.uploads.reset'
    MODEL_CREATED = 'model.created'
    MODEL_IMPORTED = 'model.imported'
    MODEL_SYNCED = 'model.synced'
    MODEL_UPDATED = 'model.updated'
    MODEL_DELETED = 'model.deleted'
    MODEL_ENABLED = 'model.enabled'
    MODEL_DISABLED = 'model.disabled'
    MODEL_ACCESS_UPDATED = 'model.access_updated'
    MODEL_PROVIDER_CONFIG_UPDATED = 'model.provider_config.updated'
    MODEL_PROVIDER_MODEL_CREATED = 'model.provider_model.created'
    MODEL_PROVIDER_MODEL_DELETED = 'model.provider_model.deleted'
    FUNCTION_CREATED = 'function.created'
    FUNCTION_UPDATED = 'function.updated'
    FUNCTION_DELETED = 'function.deleted'
    FUNCTION_ENABLED = 'function.enabled'
    FUNCTION_DISABLED = 'function.disabled'
    FUNCTION_VALVES_UPDATED = 'function.valves_updated'
    TOOL_CREATED = 'tool.created'
    TOOL_UPDATED = 'tool.updated'
    TOOL_DELETED = 'tool.deleted'
    TOOL_ACCESS_UPDATED = 'tool.access_updated'
    TOOL_VALVES_UPDATED = 'tool.valves_updated'
    SKILL_CREATED = 'skill.created'
    SKILL_UPDATED = 'skill.updated'
    SKILL_DELETED = 'skill.deleted'
    SKILL_ENABLED = 'skill.enabled'
    SKILL_DISABLED = 'skill.disabled'
    PROMPT_CREATED = 'prompt.created'
    PROMPT_UPDATED = 'prompt.updated'
    PROMPT_DELETED = 'prompt.deleted'
    PROMPT_ENABLED = 'prompt.enabled'
    PROMPT_DISABLED = 'prompt.disabled'
    PROMPT_VERSION_UPDATED = 'prompt.version_updated'
    PROMPT_ACCESS_UPDATED = 'prompt.access_updated'
    PIPELINE_UPLOADED = 'pipeline.uploaded'
    PIPELINE_ADDED = 'pipeline.added'
    PIPELINE_DELETED = 'pipeline.deleted'
    PIPELINE_VALVES_UPDATED = 'pipeline.valves_updated'
    CALENDAR_CREATED = 'calendar.created'
    CALENDAR_UPDATED = 'calendar.updated'
    CALENDAR_DELETED = 'calendar.deleted'
    CALENDAR_DEFAULT_UPDATED = 'calendar.default_updated'
    CALENDAR_EVENT_CREATED = 'calendar.event.created'
    CALENDAR_EVENT_UPDATED = 'calendar.event.updated'
    CALENDAR_EVENT_DELETED = 'calendar.event.deleted'
    CALENDAR_EVENT_RSVP_UPDATED = 'calendar.event.rsvp_updated'
    AUTOMATION_CREATED = 'automation.created'
    AUTOMATION_UPDATED = 'automation.updated'
    AUTOMATION_ENABLED = 'automation.enabled'
    AUTOMATION_DISABLED = 'automation.disabled'
    AUTOMATION_DELETED = 'automation.deleted'
    AUTOMATION_RUN_STARTED = 'automation.run_started'
    AUTOMATION_RUN_COMPLETED = 'automation.run_completed'
    AUTOMATION_RUN_FAILED = 'automation.run_failed'
    FEEDBACK_CREATED = 'feedback.created'
    FEEDBACK_UPDATED = 'feedback.updated'
    FEEDBACK_DELETED = 'feedback.deleted'
    FEEDBACK_DELETED_ALL = 'feedback.deleted_all'
    IMAGE_GENERATED = 'image.generated'
    IMAGE_EDITED = 'image.edited'
    AUDIO_SPEECH_REQUESTED = 'audio.speech_requested'
    AUDIO_TRANSCRIPTION_REQUESTED = 'audio.transcription_requested'
    TERMINAL_SESSION_OPENED = 'terminal.session.opened'
    TERMINAL_SESSION_CLOSED = 'terminal.session.closed'


EVENT_CATALOG = tuple(event.value for event in EVENTS)
EVENT_CATALOG_SET = set(EVENT_CATALOG)

SENSITIVE_KEYS = {
    'password',
    'hashed_password',
    'token',
    'access_token',
    'refresh_token',
    'id_token',
    'api_key',
    'secret',
    'key',
    'authorization',
    'cookie',
    'webhook_token',
}

SAFE_ACTOR_FIELDS = ('id', 'name', 'email', 'role', 'created_at', 'updated_at')


def normalize_event_webhook(webhook: dict[str, Any], *, create: bool = False) -> dict[str, Any]:
    now = int(time.time())
    webhook_id = str(webhook.get('id') or uuid.uuid4())
    url = str(webhook.get('url') or '').strip()

    events = [str(event).strip() for event in (webhook.get('events') or ['*']) if str(event).strip()]
    events = events or ['*']
    for event_filter in events:
        if event_filter == '*':
            continue
        if event_filter.endswith('.*'):
            prefix = event_filter[:-2]
            if prefix and any(event.startswith(f'{prefix}.') for event in EVENT_CATALOG):
                continue
            raise ValueError(f'Invalid event pattern: {event_filter}')
        if event_filter not in EVENT_CATALOG_SET:
            raise ValueError(f'Invalid event: {event_filter}')

    return {
        'id': webhook_id,
        'name': str(webhook.get('name') or ('Default webhook' if webhook_id == DEFAULT_WEBHOOK_ID else 'Webhook')),
        'url': url,
        'enabled': bool(webhook.get('enabled', True)),
        'events': events,
        'created_at': int(webhook.get('created_at') or now),
        'updated_at': now if create or webhook.get('updated_at') is None else int(webhook.get('updated_at') or now),
    }


def event_webhook_matches(webhook: dict[str, Any], event_name: str) -> bool:
    if not webhook.get('enabled', True):
        return False

    for event_filter in webhook.get('events') or ['*']:
        if event_filter == '*':
            return True
        if event_filter.endswith('.*') and event_name.startswith(f'{event_filter[:-2]}.'):
            return True
        if event_name == event_filter:
            return True
    return False


async def get_event_webhooks() -> list[dict[str, Any]]:
    webhooks = await Config.get(EVENT_WEBHOOKS_CONFIG_KEY, []) or []
    if not isinstance(webhooks, list):
        return []
    return [normalize_event_webhook(webhook) for webhook in webhooks if isinstance(webhook, dict)]


async def migrate_legacy_webhook_config() -> list[dict[str, Any]]:
    webhooks = await get_event_webhooks()
    if any(webhook.get('id') == DEFAULT_WEBHOOK_ID for webhook in webhooks):
        return webhooks

    now = int(time.time())
    legacy_url = await Config.get(LEGACY_WEBHOOK_CONFIG_KEY) or ''
    if not legacy_url:
        return webhooks

    webhooks = [
        {
            'id': DEFAULT_WEBHOOK_ID,
            'name': 'Default webhook',
            'url': legacy_url,
            'enabled': True,
            'events': ['*'],
            'created_at': now,
            'updated_at': now,
        },
        *webhooks,
    ]
    await Config.upsert({EVENT_WEBHOOKS_CONFIG_KEY: webhooks})
    return webhooks


async def upsert_event_webhook(webhook: dict[str, Any]) -> dict[str, Any]:
    webhooks = await get_event_webhooks()
    url = str(webhook.get('url') or '').strip()
    if url:
        validate_url(url)

    normalized = normalize_event_webhook(webhook, create=True)
    replaced = False
    next_webhooks = []

    for existing in webhooks:
        if existing.get('id') == normalized['id']:
            next_webhooks.append(
                {
                    **existing,
                    **normalized,
                    'created_at': existing.get('created_at') or normalized['created_at'],
                }
            )
            replaced = True
        else:
            next_webhooks.append(existing)

    if not replaced:
        next_webhooks.append(normalized)

    await Config.upsert({EVENT_WEBHOOKS_CONFIG_KEY: next_webhooks})
    return next(webhook for webhook in next_webhooks if webhook.get('id') == normalized['id'])


async def delete_event_webhook(webhook_id: str) -> bool:
    webhooks = await get_event_webhooks()
    next_webhooks = [webhook for webhook in webhooks if webhook.get('id') != webhook_id]
    if len(next_webhooks) == len(webhooks):
        return False

    values = {EVENT_WEBHOOKS_CONFIG_KEY: next_webhooks}
    if webhook_id == DEFAULT_WEBHOOK_ID:
        values[LEGACY_WEBHOOK_CONFIG_KEY] = ''

    await Config.upsert(values)
    return True


@dataclass
class Event:
    schema: str
    id: str
    event: str
    resource: str
    operation: str
    created_at: int
    instance_id: str | None
    version: str
    source: str
    actor: dict[str, Any] | None = None
    subject: dict[str, Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)
    message: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def _sensitive(key: Any) -> bool:
    normalized = str(key).lower().replace('-', '_')
    return (
        normalized in SENSITIVE_KEYS
        or normalized.endswith('_token')
        or normalized.endswith('_secret')
        or normalized.endswith('_api_key')
        or normalized.endswith('_key')
    )


def _sanitize(value: Any) -> Any:
    if hasattr(value, 'model_dump'):
        value = value.model_dump()

    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if not _sensitive(key)}

    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]

    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        return f'{value[:MAX_STRING_LENGTH]}...'

    return value


def _actor(actor: Any | None) -> dict[str, Any] | None:
    actor = _sanitize(actor)
    if not actor:
        return None

    get = actor.get if isinstance(actor, dict) else lambda key: getattr(actor, key, None)
    data = {field: get(field) for field in SAFE_ACTOR_FIELDS if get(field) is not None}
    if not data:
        return None

    data['type'] = get('type') or 'user'
    return data


def build_event(
    request_or_app: Any,
    event: EVENTS,
    *,
    actor: Any | None = None,
    subject_id: Any | None = None,
    subject_type: str | None = None,
    source: str = 'api',
    data: dict | None = None,
    message: str | None = None,
) -> Event:
    event_name = event.value
    app = getattr(request_or_app, 'app', request_or_app)
    parts = event_name.split('.')
    resource = '.'.join(parts[:-1])
    instance_id = getattr(getattr(app, 'state', None), 'instance_id', None)
    subject = (
        {'type': subject_type or resource, 'id': subject_id}
        if subject_id is not None or subject_type is not None
        else None
    )

    return Event(
        schema=VERSION,
        id=str(uuid.uuid4()),
        event=event_name,
        resource=resource,
        operation=parts[-1],
        created_at=int(time.time()),
        instance_id=instance_id,
        version=VERSION,
        source=source,
        actor=_actor(actor),
        subject=_sanitize(subject) if subject else None,
        data=_sanitize(data or {}),
        message=message,
    )


class WebhookEventSink:
    async def handle_event(self, app: Any, event: Event, request: Any | None = None) -> None:
        name = getattr(getattr(app, 'state', None), 'WEBUI_NAME', 'Open WebUI')
        subject = event.subject or {}
        subject_id = subject.get('id')
        message = event.message or f'{event.event}: {subject.get("type") or event.resource}'
        if subject_id:
            message = f'{message} ({subject_id})'

        for webhook in await get_event_webhooks():
            if webhook.get('url') and event_webhook_matches(webhook, event.event):
                try:
                    await post_webhook(name, webhook['url'], message, event.model_dump())
                except Exception:
                    log.exception('Event webhook failed for %s', webhook.get('id'))


async def dispatch_event_functions(app: Any, event: Event, request: Any | None = None) -> None:
    from open_webui.models.functions import Functions
    from open_webui.utils.plugin import get_function_module_from_cache

    context = request or SimpleNamespace(app=app)
    event_payload = event.model_dump()

    try:
        event_functions = await Functions.get_functions_by_type('event', active_only=True)
    except Exception:
        log.exception('Event functions could not be loaded for %s', event.event)
        return

    for function in event_functions:
        try:
            function_module, _, _ = await get_function_module_from_cache(context, function.id, function=function)
            handler = getattr(function_module, 'event', None)
            if not handler:
                continue

            if hasattr(function_module, 'valves') and hasattr(function_module, 'Valves'):
                valves = await Functions.get_function_valves_by_id(function.id)
                function_module.valves = function_module.Valves(**(valves if valves else {}))

            sig = inspect.signature(handler)
            accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values())
            extra_params = {
                'event': event_payload,
                '__id__': function.id,
                '__event__': event,
                '__event_id__': event.id,
                '__event_name__': event.event,
                '__app__': app,
                '__request__': request,
            }
            params = {
                key: value for key, value in extra_params.items() if accepts_kwargs or key in sig.parameters
            }

            if inspect.iscoroutinefunction(handler):
                await handler(**params)
            else:
                handler(**params)
        except Exception:
            log.exception('Event function failed for %s', function.id)


def schedule_event_function_dispatch(app: Any, event: Event, request: Any | None = None) -> None:
    try:
        asyncio.create_task(dispatch_event_functions(app, event, request))
    except RuntimeError:
        log.exception('Event functions could not be scheduled for %s', event.event)


class EventFunctionSink:
    async def handle_event(self, app: Any, event: Event, request: Any | None = None) -> None:
        schedule_event_function_dispatch(app, event, request)


EVENT_SINKS = [EventFunctionSink(), WebhookEventSink()]


async def publish_event(
    request_or_app: Any,
    event: EVENTS,
    *,
    actor: Any | None = None,
    subject_id: Any | None = None,
    subject_type: str | None = None,
    source: str = 'api',
    data: dict | None = None,
    message: str | None = None,
) -> None:
    app = getattr(request_or_app, 'app', request_or_app)
    request = request_or_app if hasattr(request_or_app, 'app') else None
    event_payload = build_event(
        request_or_app,
        event,
        actor=actor,
        subject_id=subject_id,
        subject_type=subject_type,
        source=source,
        data=data,
        message=message,
    )

    for sink in EVENT_SINKS:
        try:
            await sink.handle_event(app, event_payload, request=request)
        except Exception:
            log.exception('Event sink failed for %s', event.value)
