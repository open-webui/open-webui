from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from types import SimpleNamespace
from typing import Any

from open_webui.env import VERSION
from open_webui.models.config import Config
from pydantic import BaseModel, ConfigDict, Field, model_validator
from open_webui.retrieval.web.utils import validate_url
from open_webui.utils.webhook import post_webhook

log = logging.getLogger(__name__)

MAX_STRING_LENGTH = 1000
EVENT_WEBHOOKS_CONFIG_KEY = 'events.webhooks'
LEGACY_WEBHOOK_CONFIG_KEY = 'webhook_url'
DEFAULT_WEBHOOK_ID = 'default'


class EventDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    message: str | None = None

    @model_validator(mode='after')
    def defaults(self) -> 'EventDefinition':
        title = self.name.replace('.', ' ').replace('_', ' ').title()
        if self.description is None:
            object.__setattr__(self, 'description', f'{title}.')
        if self.message is None:
            object.__setattr__(self, 'message', title)
        return self


class EventDefinitions(BaseModel):
    model_config = ConfigDict(frozen=True)

    SYSTEM_STARTUP_STARTED: EventDefinition = EventDefinition(name='system.startup.started')
    SYSTEM_STARTUP_COMPLETED: EventDefinition = EventDefinition(name='system.startup.completed')
    SYSTEM_SHUTDOWN_STARTED: EventDefinition = EventDefinition(name='system.shutdown.started')
    SYSTEM_SHUTDOWN_COMPLETED: EventDefinition = EventDefinition(name='system.shutdown.completed')
    CONFIG_IMPORTED: EventDefinition = EventDefinition(name='config.imported')
    CONFIG_UPDATED: EventDefinition = EventDefinition(name='config.updated')
    CONFIG_WEBHOOK_UPDATED: EventDefinition = EventDefinition(name='config.webhook.updated')
    CONFIG_CONNECTIONS_UPDATED: EventDefinition = EventDefinition(name='config.connections.updated')
    CONFIG_TOOL_SERVERS_UPDATED: EventDefinition = EventDefinition(name='config.tool_servers.updated')
    CONFIG_TERMINAL_SERVERS_UPDATED: EventDefinition = EventDefinition(name='config.terminal_servers.updated')
    CONFIG_CODE_EXECUTION_UPDATED: EventDefinition = EventDefinition(name='config.code_execution.updated')
    CONFIG_MODELS_UPDATED: EventDefinition = EventDefinition(name='config.models.updated')
    CONFIG_BANNERS_UPDATED: EventDefinition = EventDefinition(name='config.banners.updated')
    CONFIG_SUGGESTIONS_UPDATED: EventDefinition = EventDefinition(name='config.suggestions.updated')
    AUTH_SIGNUP: EventDefinition = EventDefinition(name='auth.signup')
    AUTH_LOGIN: EventDefinition = EventDefinition(name='auth.login')
    AUTH_LOGOUT: EventDefinition = EventDefinition(name='auth.logout')
    AUTH_PASSWORD_CHANGED: EventDefinition = EventDefinition(name='auth.password_changed')
    AUTH_API_KEY_CREATED: EventDefinition = EventDefinition(name='auth.api_key.created')
    AUTH_API_KEY_DELETED: EventDefinition = EventDefinition(name='auth.api_key.deleted')
    AUTH_OAUTH_SESSION_DELETED: EventDefinition = EventDefinition(name='auth.oauth_session.deleted')
    USER_CREATED: EventDefinition = EventDefinition(name='user.created', description='A user account was created.', message='User created')
    USER_UPDATED: EventDefinition = EventDefinition(name='user.updated')
    USER_DELETED: EventDefinition = EventDefinition(name='user.deleted')
    USER_ROLE_UPDATED: EventDefinition = EventDefinition(name='user.role_updated')
    USER_STATUS_UPDATED: EventDefinition = EventDefinition(name='user.status_updated')
    USER_SETTINGS_UPDATED: EventDefinition = EventDefinition(name='user.settings_updated')
    USER_PROFILE_UPDATED: EventDefinition = EventDefinition(name='user.profile_updated')
    USER_PERMISSIONS_UPDATED: EventDefinition = EventDefinition(name='user.permissions_updated')
    GROUP_CREATED: EventDefinition = EventDefinition(name='group.created')
    GROUP_UPDATED: EventDefinition = EventDefinition(name='group.updated')
    GROUP_DELETED: EventDefinition = EventDefinition(name='group.deleted')
    GROUP_MEMBER_ADDED: EventDefinition = EventDefinition(name='group.member_added')
    GROUP_MEMBER_REMOVED: EventDefinition = EventDefinition(name='group.member_removed')
    CHAT_CREATED: EventDefinition = EventDefinition(name='chat.created')
    CHAT_IMPORTED: EventDefinition = EventDefinition(name='chat.imported')
    CHAT_UPDATED: EventDefinition = EventDefinition(name='chat.updated')
    CHAT_DELETED: EventDefinition = EventDefinition(name='chat.deleted')
    CHAT_DELETED_ALL: EventDefinition = EventDefinition(name='chat.deleted_all')
    CHAT_COMPACTED: EventDefinition = EventDefinition(name='chat.compacted')
    CHAT_PINNED: EventDefinition = EventDefinition(name='chat.pinned')
    CHAT_UNPINNED: EventDefinition = EventDefinition(name='chat.unpinned')
    CHAT_CLONED: EventDefinition = EventDefinition(name='chat.cloned')
    CHAT_ARCHIVED: EventDefinition = EventDefinition(name='chat.archived')
    CHAT_UNARCHIVED: EventDefinition = EventDefinition(name='chat.unarchived')
    CHAT_SHARED: EventDefinition = EventDefinition(name='chat.shared')
    CHAT_UNSHARED: EventDefinition = EventDefinition(name='chat.unshared')
    CHAT_FOLDER_UPDATED: EventDefinition = EventDefinition(name='chat.folder_updated')
    CHAT_TAG_ADDED: EventDefinition = EventDefinition(name='chat.tag_added')
    CHAT_TAG_REMOVED: EventDefinition = EventDefinition(name='chat.tag_removed')
    MESSAGE_CREATED: EventDefinition = EventDefinition(name='message.created')
    MESSAGE_UPDATED: EventDefinition = EventDefinition(name='message.updated')
    MESSAGE_DELETED: EventDefinition = EventDefinition(name='message.deleted')
    MESSAGE_EVENT_RECEIVED: EventDefinition = EventDefinition(name='message.event_received')
    MESSAGE_REACTION_ADDED: EventDefinition = EventDefinition(name='message.reaction_added')
    MESSAGE_REACTION_REMOVED: EventDefinition = EventDefinition(name='message.reaction_removed')
    MESSAGE_PINNED: EventDefinition = EventDefinition(name='message.pinned')
    MESSAGE_UNPINNED: EventDefinition = EventDefinition(name='message.unpinned')
    CHANNEL_CREATED: EventDefinition = EventDefinition(name='channel.created')
    CHANNEL_UPDATED: EventDefinition = EventDefinition(name='channel.updated')
    CHANNEL_DELETED: EventDefinition = EventDefinition(name='channel.deleted')
    CHANNEL_MEMBER_ADDED: EventDefinition = EventDefinition(name='channel.member_added')
    CHANNEL_MEMBER_REMOVED: EventDefinition = EventDefinition(name='channel.member_removed')
    CHANNEL_MEMBER_ACTIVE_UPDATED: EventDefinition = EventDefinition(name='channel.member_active_updated')
    CHANNEL_WEBHOOK_CREATED: EventDefinition = EventDefinition(name='channel.webhook.created')
    CHANNEL_WEBHOOK_UPDATED: EventDefinition = EventDefinition(name='channel.webhook.updated')
    CHANNEL_WEBHOOK_DELETED: EventDefinition = EventDefinition(name='channel.webhook.deleted')
    FILE_UPLOADED: EventDefinition = EventDefinition(name='file.uploaded')
    FILE_CONTENT_UPDATED: EventDefinition = EventDefinition(name='file.content_updated')
    FILE_RENAMED: EventDefinition = EventDefinition(name='file.renamed')
    FILE_DELETED: EventDefinition = EventDefinition(name='file.deleted')
    FILE_DELETED_ALL: EventDefinition = EventDefinition(name='file.deleted_all')
    FOLDER_CREATED: EventDefinition = EventDefinition(name='folder.created')
    FOLDER_UPDATED: EventDefinition = EventDefinition(name='folder.updated')
    FOLDER_PARENT_UPDATED: EventDefinition = EventDefinition(name='folder.parent_updated')
    FOLDER_ACCESS_UPDATED: EventDefinition = EventDefinition(name='folder.access_updated')
    FOLDER_DELETED: EventDefinition = EventDefinition(name='folder.deleted')
    NOTE_CREATED: EventDefinition = EventDefinition(name='note.created')
    NOTE_UPDATED: EventDefinition = EventDefinition(name='note.updated')
    NOTE_ACCESS_UPDATED: EventDefinition = EventDefinition(name='note.access_updated')
    NOTE_PINNED: EventDefinition = EventDefinition(name='note.pinned')
    NOTE_UNPINNED: EventDefinition = EventDefinition(name='note.unpinned')
    NOTE_DELETED: EventDefinition = EventDefinition(name='note.deleted')
    MEMORY_CREATED: EventDefinition = EventDefinition(name='memory.created')
    MEMORY_UPDATED: EventDefinition = EventDefinition(name='memory.updated')
    MEMORY_DELETED: EventDefinition = EventDefinition(name='memory.deleted')
    MEMORY_RESET: EventDefinition = EventDefinition(name='memory.reset')
    KNOWLEDGE_CREATED: EventDefinition = EventDefinition(name='knowledge.created')
    KNOWLEDGE_UPDATED: EventDefinition = EventDefinition(name='knowledge.updated')
    KNOWLEDGE_DELETED: EventDefinition = EventDefinition(name='knowledge.deleted')
    KNOWLEDGE_RESET: EventDefinition = EventDefinition(name='knowledge.reset')
    KNOWLEDGE_REINDEXED: EventDefinition = EventDefinition(name='knowledge.reindexed')
    KNOWLEDGE_ACCESS_UPDATED: EventDefinition = EventDefinition(name='knowledge.access_updated')
    KNOWLEDGE_FILE_ADDED: EventDefinition = EventDefinition(name='knowledge.file.added')
    KNOWLEDGE_FILE_UPDATED: EventDefinition = EventDefinition(name='knowledge.file.updated')
    KNOWLEDGE_FILE_REMOVED: EventDefinition = EventDefinition(name='knowledge.file.removed')
    KNOWLEDGE_FILE_MOVED: EventDefinition = EventDefinition(name='knowledge.file.moved')
    KNOWLEDGE_DIRECTORY_CREATED: EventDefinition = EventDefinition(name='knowledge.directory.created')
    KNOWLEDGE_DIRECTORY_UPDATED: EventDefinition = EventDefinition(name='knowledge.directory.updated')
    KNOWLEDGE_DIRECTORY_DELETED: EventDefinition = EventDefinition(name='knowledge.directory.deleted')
    KNOWLEDGE_EXTERNAL_CONNECTION_CREATED: EventDefinition = EventDefinition(name='knowledge.external_connection.created')
    KNOWLEDGE_EXTERNAL_CONNECTION_UPDATED: EventDefinition = EventDefinition(name='knowledge.external_connection.updated')
    KNOWLEDGE_EXTERNAL_CONNECTION_DELETED: EventDefinition = EventDefinition(name='knowledge.external_connection.deleted')
    RETRIEVAL_CONTENT_PROCESSED: EventDefinition = EventDefinition(name='retrieval.content.processed')
    RETRIEVAL_COLLECTION_DELETED: EventDefinition = EventDefinition(name='retrieval.collection.deleted')
    RETRIEVAL_VECTOR_DB_RESET: EventDefinition = EventDefinition(name='retrieval.vector_db.reset')
    RETRIEVAL_UPLOADS_RESET: EventDefinition = EventDefinition(name='retrieval.uploads.reset')
    MODEL_CREATED: EventDefinition = EventDefinition(name='model.created')
    MODEL_IMPORTED: EventDefinition = EventDefinition(name='model.imported')
    MODEL_SYNCED: EventDefinition = EventDefinition(name='model.synced')
    MODEL_UPDATED: EventDefinition = EventDefinition(name='model.updated')
    MODEL_DELETED: EventDefinition = EventDefinition(name='model.deleted')
    MODEL_ENABLED: EventDefinition = EventDefinition(name='model.enabled')
    MODEL_DISABLED: EventDefinition = EventDefinition(name='model.disabled')
    MODEL_ACCESS_UPDATED: EventDefinition = EventDefinition(name='model.access_updated')
    MODEL_PROVIDER_CONFIG_UPDATED: EventDefinition = EventDefinition(name='model.provider_config.updated')
    MODEL_PROVIDER_MODEL_CREATED: EventDefinition = EventDefinition(name='model.provider_model.created')
    MODEL_PROVIDER_MODEL_DELETED: EventDefinition = EventDefinition(name='model.provider_model.deleted')
    FUNCTION_CREATED: EventDefinition = EventDefinition(name='function.created')
    FUNCTION_UPDATED: EventDefinition = EventDefinition(name='function.updated')
    FUNCTION_DELETED: EventDefinition = EventDefinition(name='function.deleted')
    FUNCTION_ENABLED: EventDefinition = EventDefinition(name='function.enabled')
    FUNCTION_DISABLED: EventDefinition = EventDefinition(name='function.disabled')
    FUNCTION_VALVES_UPDATED: EventDefinition = EventDefinition(name='function.valves_updated')
    TOOL_CREATED: EventDefinition = EventDefinition(name='tool.created')
    TOOL_UPDATED: EventDefinition = EventDefinition(name='tool.updated')
    TOOL_DELETED: EventDefinition = EventDefinition(name='tool.deleted')
    TOOL_ACCESS_UPDATED: EventDefinition = EventDefinition(name='tool.access_updated')
    TOOL_VALVES_UPDATED: EventDefinition = EventDefinition(name='tool.valves_updated')
    SKILL_CREATED: EventDefinition = EventDefinition(name='skill.created')
    SKILL_UPDATED: EventDefinition = EventDefinition(name='skill.updated')
    SKILL_DELETED: EventDefinition = EventDefinition(name='skill.deleted')
    SKILL_ENABLED: EventDefinition = EventDefinition(name='skill.enabled')
    SKILL_DISABLED: EventDefinition = EventDefinition(name='skill.disabled')
    PROMPT_CREATED: EventDefinition = EventDefinition(name='prompt.created')
    PROMPT_UPDATED: EventDefinition = EventDefinition(name='prompt.updated')
    PROMPT_DELETED: EventDefinition = EventDefinition(name='prompt.deleted')
    PROMPT_ENABLED: EventDefinition = EventDefinition(name='prompt.enabled')
    PROMPT_DISABLED: EventDefinition = EventDefinition(name='prompt.disabled')
    PROMPT_VERSION_UPDATED: EventDefinition = EventDefinition(name='prompt.version_updated')
    PROMPT_ACCESS_UPDATED: EventDefinition = EventDefinition(name='prompt.access_updated')
    PIPELINE_UPLOADED: EventDefinition = EventDefinition(name='pipeline.uploaded')
    PIPELINE_ADDED: EventDefinition = EventDefinition(name='pipeline.added')
    PIPELINE_DELETED: EventDefinition = EventDefinition(name='pipeline.deleted')
    PIPELINE_VALVES_UPDATED: EventDefinition = EventDefinition(name='pipeline.valves_updated')
    CALENDAR_CREATED: EventDefinition = EventDefinition(name='calendar.created')
    CALENDAR_UPDATED: EventDefinition = EventDefinition(name='calendar.updated')
    CALENDAR_DELETED: EventDefinition = EventDefinition(name='calendar.deleted')
    CALENDAR_DEFAULT_UPDATED: EventDefinition = EventDefinition(name='calendar.default_updated')
    CALENDAR_EVENT_CREATED: EventDefinition = EventDefinition(name='calendar.event.created')
    CALENDAR_EVENT_UPDATED: EventDefinition = EventDefinition(name='calendar.event.updated')
    CALENDAR_EVENT_DELETED: EventDefinition = EventDefinition(name='calendar.event.deleted')
    CALENDAR_EVENT_RSVP_UPDATED: EventDefinition = EventDefinition(name='calendar.event.rsvp_updated')
    AUTOMATION_CREATED: EventDefinition = EventDefinition(name='automation.created')
    AUTOMATION_UPDATED: EventDefinition = EventDefinition(name='automation.updated')
    AUTOMATION_ENABLED: EventDefinition = EventDefinition(name='automation.enabled')
    AUTOMATION_DISABLED: EventDefinition = EventDefinition(name='automation.disabled')
    AUTOMATION_DELETED: EventDefinition = EventDefinition(name='automation.deleted')
    AUTOMATION_RUN_STARTED: EventDefinition = EventDefinition(name='automation.run_started')
    AUTOMATION_RUN_COMPLETED: EventDefinition = EventDefinition(name='automation.run_completed')
    AUTOMATION_RUN_FAILED: EventDefinition = EventDefinition(name='automation.run_failed')
    FEEDBACK_CREATED: EventDefinition = EventDefinition(name='feedback.created')
    FEEDBACK_UPDATED: EventDefinition = EventDefinition(name='feedback.updated')
    FEEDBACK_DELETED: EventDefinition = EventDefinition(name='feedback.deleted')
    FEEDBACK_DELETED_ALL: EventDefinition = EventDefinition(name='feedback.deleted_all')
    IMAGE_GENERATED: EventDefinition = EventDefinition(name='image.generated')
    IMAGE_EDITED: EventDefinition = EventDefinition(name='image.edited')
    AUDIO_SPEECH_REQUESTED: EventDefinition = EventDefinition(name='audio.speech_requested')
    AUDIO_TRANSCRIPTION_REQUESTED: EventDefinition = EventDefinition(name='audio.transcription_requested')
    TERMINAL_SESSION_OPENED: EventDefinition = EventDefinition(name='terminal.session.opened')
    TERMINAL_SESSION_CLOSED: EventDefinition = EventDefinition(name='terminal.session.closed')


EVENTS = EventDefinitions()
EVENT_DEFINITIONS = tuple(getattr(EVENTS, field_name) for field_name in EventDefinitions.model_fields)
EVENT_DEFINITIONS_BY_NAME = {definition.name: definition for definition in EVENT_DEFINITIONS}
EVENT_CATALOG = tuple(definition.name for definition in EVENT_DEFINITIONS)
EVENT_CATALOG_SET = set(EVENT_CATALOG)


def get_event_catalog() -> list[dict[str, str]]:
    return [
        {
            'event': definition.name,
            'description': definition.description,
            'message': definition.message,
        }
        for definition in EVENT_DEFINITIONS
    ]

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

    targets = normalize_event_targets(webhook.get('targets'))

    return {
        'id': webhook_id,
        'name': str(webhook.get('name') or ('Default webhook' if webhook_id == DEFAULT_WEBHOOK_ID else 'Webhook')),
        'url': url,
        'enabled': bool(webhook.get('enabled', True)),
        'events': events,
        'targets': targets,
        'created_at': int(webhook.get('created_at') or now),
        'updated_at': now if create or webhook.get('updated_at') is None else int(webhook.get('updated_at') or now),
    }


def normalize_event_targets(targets: Any) -> list[dict[str, str]] | None:
    if targets is None:
        return None
    if not isinstance(targets, list):
        raise ValueError('Invalid targets')

    normalized = []
    seen = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError('Invalid target')

        target_type = str(target.get('type') or '').strip()
        target_id = str(target.get('id') or '').strip()
        if target_type not in {'user', 'group'} or not target_id:
            raise ValueError('Invalid target')

        key = (target_type, target_id)
        if key in seen:
            continue

        normalized.append({'type': target_type, 'id': target_id})
        seen.add(key)

    return normalized


def event_filter_matches(webhook: dict[str, Any], event_name: str) -> bool:
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


def event_user_ids(event: 'Event') -> set[str]:
    user_ids = set()
    actor = event.actor or {}
    subject = event.subject or {}
    data = event.data or {}

    if actor.get('id'):
        user_ids.add(str(actor['id']))

    if subject.get('type') == 'user' and subject.get('id'):
        user_ids.add(str(subject['id']))

    if data.get('user_id'):
        user_ids.add(str(data['user_id']))

    for user_id in data.get('user_ids') or []:
        if user_id:
            user_ids.add(str(user_id))

    return user_ids


async def event_target_matches(
    targets: list[dict[str, str]] | None,
    user_ids: set[str],
    user_group_ids: dict[str, set[str]] | None = None,
) -> bool:
    if targets is None:
        return True
    if not targets:
        return False
    if not user_ids:
        return False

    target_user_ids = {target['id'] for target in targets if target.get('type') == 'user'}
    if target_user_ids.intersection(user_ids):
        return True

    target_group_ids = {target['id'] for target in targets if target.get('type') == 'group'}
    if not target_group_ids:
        return False

    if user_group_ids is None:
        from open_webui.models.groups import Groups

        groups_by_user = await Groups.get_groups_by_member_ids(list(user_ids))
        user_group_ids = {
            user_id: {group.id for group in groups}
            for user_id, groups in groups_by_user.items()
        }

    return any(group_ids.intersection(target_group_ids) for group_ids in user_group_ids.values())


async def event_webhook_matches(webhook: dict[str, Any], event: 'Event') -> bool:
    if not event_filter_matches(webhook, event.event):
        return False

    return await event_target_matches(webhook.get('targets'), event_user_ids(event))


async def get_event_webhooks() -> list[dict[str, Any]]:
    webhooks = await Config.get(EVENT_WEBHOOKS_CONFIG_KEY, []) or []
    if not isinstance(webhooks, list):
        return []

    normalized = []
    for webhook in webhooks:
        if not isinstance(webhook, dict):
            continue
        try:
            normalized.append(normalize_event_webhook(webhook))
        except ValueError:
            log.exception('Invalid event webhook config skipped')
    return normalized


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
            'targets': None,
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


class Event(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias='schema')
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
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        return super().model_dump(*args, **kwargs)


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


def event_name(event: EventDefinition | str) -> str:
    name = event.name if isinstance(event, EventDefinition) else str(event)
    if name not in EVENT_CATALOG_SET:
        raise ValueError(f'Unknown event: {name}')
    return name


def build_event(
    request_or_app: Any,
    event: EventDefinition | str,
    *,
    actor: Any | None = None,
    subject_id: Any | None = None,
    subject_type: str | None = None,
    source: str = 'api',
    data: dict | None = None,
    message: str | None = None,
) -> Event:
    event_name_value = event_name(event)
    app = getattr(request_or_app, 'app', request_or_app)
    parts = event_name_value.split('.')
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
        event=event_name_value,
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


async def dispatch_webhook_event(app: Any, event: Event) -> None:
    name = getattr(getattr(app, 'state', None), 'WEBUI_NAME', 'Open WebUI')
    subject = event.subject or {}
    subject_id = subject.get('id')
    definition = EVENT_DEFINITIONS_BY_NAME.get(event.event)
    message = event.message or (definition.message if definition else event.event)
    if subject_id:
        message = f'{message} ({subject_id})'

    for webhook in await get_event_webhooks():
        if not webhook.get('url') or not await event_webhook_matches(webhook, event):
            continue

        try:
            await post_webhook(name, webhook['url'], message, event.model_dump())
        except Exception:
            log.exception('Event webhook failed for %s', webhook.get('id'))


def schedule_webhook_dispatch(app: Any, event: Event) -> None:
    try:
        asyncio.create_task(dispatch_webhook_event(app, event))
    except RuntimeError:
        log.exception('Event webhook delivery could not be scheduled for %s', event.event)


class WebhookEventSink:
    async def handle_event(self, app: Any, event: Event, request: Any | None = None) -> None:
        schedule_webhook_dispatch(app, event)


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
    event: EventDefinition | str,
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
            log.exception('Event sink failed for %s', event_payload.event)
