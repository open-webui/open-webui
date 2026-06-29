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

    SYSTEM_STARTUP_STARTED: EventDefinition = EventDefinition(
        name='system.startup.started', description='Application startup began.', message='Startup started'
    )
    SYSTEM_STARTUP_COMPLETED: EventDefinition = EventDefinition(
        name='system.startup.completed', description='Application startup completed.', message='Startup completed'
    )
    SYSTEM_SHUTDOWN_STARTED: EventDefinition = EventDefinition(
        name='system.shutdown.started', description='Application shutdown began.', message='Shutdown started'
    )
    SYSTEM_SHUTDOWN_COMPLETED: EventDefinition = EventDefinition(
        name='system.shutdown.completed', description='Application shutdown completed.', message='Shutdown completed'
    )
    CONFIG_IMPORTED: EventDefinition = EventDefinition(
        name='config.imported', description='Configuration was imported.', message='Config imported'
    )
    CONFIG_UPDATED: EventDefinition = EventDefinition(
        name='config.updated', description='Configuration was updated.', message='Config updated'
    )
    CONFIG_WEBHOOK_UPDATED: EventDefinition = EventDefinition(
        name='config.webhook.updated',
        description='Event webhook configuration was updated.',
        message='Webhook configuration updated',
    )
    CONFIG_CONNECTIONS_UPDATED: EventDefinition = EventDefinition(
        name='config.connections.updated',
        description='Connection configuration was updated.',
        message='Config Connections updated',
    )
    CONFIG_TOOL_SERVERS_UPDATED: EventDefinition = EventDefinition(
        name='config.tool_servers.updated',
        description='Tool server configuration was updated.',
        message='Config Tool Servers updated',
    )
    CONFIG_TERMINAL_SERVERS_UPDATED: EventDefinition = EventDefinition(
        name='config.terminal_servers.updated',
        description='Terminal server configuration was updated.',
        message='Config Terminal Servers updated',
    )
    CONFIG_CODE_EXECUTION_UPDATED: EventDefinition = EventDefinition(
        name='config.code_execution.updated',
        description='Code execution configuration was updated.',
        message='Config Code Execution updated',
    )
    CONFIG_MODELS_UPDATED: EventDefinition = EventDefinition(
        name='config.models.updated', description='Model configuration was updated.', message='Config Models updated'
    )
    CONFIG_BANNERS_UPDATED: EventDefinition = EventDefinition(
        name='config.banners.updated', description='Banner configuration was updated.', message='Config Banners updated'
    )
    CONFIG_SUGGESTIONS_UPDATED: EventDefinition = EventDefinition(
        name='config.suggestions.updated',
        description='Suggestion configuration was updated.',
        message='Config Suggestions updated',
    )
    AUTH_SIGNUP: EventDefinition = EventDefinition(
        name='auth.signup', description='A user account was created through signup.', message='User signed up'
    )
    AUTH_LOGIN: EventDefinition = EventDefinition(
        name='auth.login', description='A user successfully logged in.', message='User logged in'
    )
    AUTH_LOGOUT: EventDefinition = EventDefinition(
        name='auth.logout', description='A user logged out.', message='User logged out'
    )
    AUTH_PASSWORD_CHANGED: EventDefinition = EventDefinition(
        name='auth.password_changed', description='A user password was changed.', message='Password changed'
    )
    AUTH_API_KEY_CREATED: EventDefinition = EventDefinition(
        name='auth.api_key.created', description='A user API key was created.', message='API key created'
    )
    AUTH_API_KEY_DELETED: EventDefinition = EventDefinition(
        name='auth.api_key.deleted', description='A user API key was deleted.', message='API key deleted'
    )
    AUTH_OAUTH_SESSION_DELETED: EventDefinition = EventDefinition(
        name='auth.oauth_session.deleted', description='An OAuth session was deleted.', message='OAuth session deleted'
    )
    USER_CREATED: EventDefinition = EventDefinition(
        name='user.created', description='A user account was created.', message='User created'
    )
    USER_UPDATED: EventDefinition = EventDefinition(
        name='user.updated', description='A user account was updated.', message='User updated'
    )
    USER_DELETED: EventDefinition = EventDefinition(
        name='user.deleted', description='A user account was deleted.', message='User deleted'
    )
    USER_ROLE_UPDATED: EventDefinition = EventDefinition(
        name='user.role_updated', description='A user role was updated.', message='User role updated'
    )
    USER_STATUS_UPDATED: EventDefinition = EventDefinition(
        name='user.status_updated', description='A user status was updated.', message='User status updated'
    )
    USER_SETTINGS_UPDATED: EventDefinition = EventDefinition(
        name='user.settings_updated', description='A user settings object was updated.', message='User settings updated'
    )
    USER_PROFILE_UPDATED: EventDefinition = EventDefinition(
        name='user.profile_updated', description='A user profile was updated.', message='User profile updated'
    )
    USER_PERMISSIONS_UPDATED: EventDefinition = EventDefinition(
        name='user.permissions_updated',
        description='A user permissions object was updated.',
        message='User permissions updated',
    )
    GROUP_CREATED: EventDefinition = EventDefinition(
        name='group.created', description='A group was created.', message='Group created'
    )
    GROUP_UPDATED: EventDefinition = EventDefinition(
        name='group.updated', description='A group was updated.', message='Group updated'
    )
    GROUP_DELETED: EventDefinition = EventDefinition(
        name='group.deleted', description='A group was deleted.', message='Group deleted'
    )
    GROUP_MEMBER_ADDED: EventDefinition = EventDefinition(
        name='group.member_added', description='A user was added to a group.', message='Group member added'
    )
    GROUP_MEMBER_REMOVED: EventDefinition = EventDefinition(
        name='group.member_removed', description='A user was removed from a group.', message='Group member removed'
    )
    CHAT_CREATED: EventDefinition = EventDefinition(
        name='chat.created', description='A chat was created.', message='Chat created'
    )
    CHAT_IMPORTED: EventDefinition = EventDefinition(
        name='chat.imported', description='A chat was imported.', message='Chat imported'
    )
    CHAT_UPDATED: EventDefinition = EventDefinition(
        name='chat.updated', description='A chat was updated.', message='Chat updated'
    )
    CHAT_DELETED: EventDefinition = EventDefinition(
        name='chat.deleted', description='A chat was deleted.', message='Chat deleted'
    )
    CHAT_DELETED_ALL: EventDefinition = EventDefinition(
        name='chat.deleted_all', description='All chats for a scope were deleted.', message='Chat deleted all'
    )
    CHAT_COMPACTED: EventDefinition = EventDefinition(
        name='chat.compacted', description='A chat was compacted.', message='Chat compacted'
    )
    CHAT_PINNED: EventDefinition = EventDefinition(
        name='chat.pinned', description='A chat was pinned.', message='Chat pinned'
    )
    CHAT_UNPINNED: EventDefinition = EventDefinition(
        name='chat.unpinned', description='A chat was unpinned.', message='Chat unpinned'
    )
    CHAT_CLONED: EventDefinition = EventDefinition(
        name='chat.cloned', description='A chat was cloned.', message='Chat cloned'
    )
    CHAT_ARCHIVED: EventDefinition = EventDefinition(
        name='chat.archived', description='A chat was archived.', message='Chat archived'
    )
    CHAT_UNARCHIVED: EventDefinition = EventDefinition(
        name='chat.unarchived', description='A chat was unarchived.', message='Chat unarchived'
    )
    CHAT_SHARED: EventDefinition = EventDefinition(
        name='chat.shared', description='A chat was shared.', message='Chat shared'
    )
    CHAT_UNSHARED: EventDefinition = EventDefinition(
        name='chat.unshared', description='A chat was unshared.', message='Chat unshared'
    )
    CHAT_FOLDER_UPDATED: EventDefinition = EventDefinition(
        name='chat.folder_updated', description='A chat folder assignment was updated.', message='Chat folder updated'
    )
    CHAT_TAG_ADDED: EventDefinition = EventDefinition(
        name='chat.tag_added', description='A tag was added to a chat.', message='Chat tag added'
    )
    CHAT_TAG_REMOVED: EventDefinition = EventDefinition(
        name='chat.tag_removed', description='A tag was removed from a chat.', message='Chat tag removed'
    )
    MESSAGE_CREATED: EventDefinition = EventDefinition(
        name='message.created', description='A message was created.', message='Message created'
    )
    MESSAGE_UPDATED: EventDefinition = EventDefinition(
        name='message.updated', description='A message was updated.', message='Message updated'
    )
    MESSAGE_DELETED: EventDefinition = EventDefinition(
        name='message.deleted', description='A message was deleted.', message='Message deleted'
    )
    MESSAGE_EVENT_RECEIVED: EventDefinition = EventDefinition(
        name='message.event_received',
        description='A message-level event was received.',
        message='Message event received',
    )
    MESSAGE_REACTION_ADDED: EventDefinition = EventDefinition(
        name='message.reaction_added',
        description='A reaction was added to a message.',
        message='Message reaction added',
    )
    MESSAGE_REACTION_REMOVED: EventDefinition = EventDefinition(
        name='message.reaction_removed',
        description='A reaction was removed from a message.',
        message='Message reaction removed',
    )
    MESSAGE_PINNED: EventDefinition = EventDefinition(
        name='message.pinned', description='A message was pinned.', message='Message pinned'
    )
    MESSAGE_UNPINNED: EventDefinition = EventDefinition(
        name='message.unpinned', description='A message was unpinned.', message='Message unpinned'
    )
    CHANNEL_CREATED: EventDefinition = EventDefinition(
        name='channel.created', description='A channel was created.', message='Channel created'
    )
    CHANNEL_UPDATED: EventDefinition = EventDefinition(
        name='channel.updated', description='A channel was updated.', message='Channel updated'
    )
    CHANNEL_DELETED: EventDefinition = EventDefinition(
        name='channel.deleted', description='A channel was deleted.', message='Channel deleted'
    )
    CHANNEL_MEMBER_ADDED: EventDefinition = EventDefinition(
        name='channel.member_added', description='A member was added to a channel.', message='Channel member added'
    )
    CHANNEL_MEMBER_REMOVED: EventDefinition = EventDefinition(
        name='channel.member_removed',
        description='A member was removed from a channel.',
        message='Channel member removed',
    )
    CHANNEL_MEMBER_ACTIVE_UPDATED: EventDefinition = EventDefinition(
        name='channel.member_active_updated',
        description='A channel member active state was updated.',
        message='Channel member active updated',
    )
    CHANNEL_WEBHOOK_CREATED: EventDefinition = EventDefinition(
        name='channel.webhook.created',
        description='A channel incoming webhook was created.',
        message='Channel Webhook created',
    )
    CHANNEL_WEBHOOK_UPDATED: EventDefinition = EventDefinition(
        name='channel.webhook.updated',
        description='A channel incoming webhook was updated.',
        message='Channel Webhook updated',
    )
    CHANNEL_WEBHOOK_DELETED: EventDefinition = EventDefinition(
        name='channel.webhook.deleted',
        description='A channel incoming webhook was deleted.',
        message='Channel Webhook deleted',
    )
    FILE_UPLOADED: EventDefinition = EventDefinition(
        name='file.uploaded', description='A file was uploaded.', message='File uploaded'
    )
    FILE_CONTENT_UPDATED: EventDefinition = EventDefinition(
        name='file.content_updated', description='File content was updated.', message='File content updated'
    )
    FILE_RENAMED: EventDefinition = EventDefinition(
        name='file.renamed', description='A file was renamed.', message='File renamed'
    )
    FILE_DELETED: EventDefinition = EventDefinition(
        name='file.deleted', description='A file was deleted.', message='File deleted'
    )
    FILE_DELETED_ALL: EventDefinition = EventDefinition(
        name='file.deleted_all', description='All files for a scope were deleted.', message='File deleted all'
    )
    FOLDER_CREATED: EventDefinition = EventDefinition(
        name='folder.created', description='A folder was created.', message='Folder created'
    )
    FOLDER_UPDATED: EventDefinition = EventDefinition(
        name='folder.updated', description='A folder was updated.', message='Folder updated'
    )
    FOLDER_PARENT_UPDATED: EventDefinition = EventDefinition(
        name='folder.parent_updated', description='A folder parent was updated.', message='Folder parent updated'
    )
    FOLDER_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='folder.access_updated', description='Folder access was updated.', message='Folder access updated'
    )
    FOLDER_DELETED: EventDefinition = EventDefinition(
        name='folder.deleted', description='A folder was deleted.', message='Folder deleted'
    )
    NOTE_CREATED: EventDefinition = EventDefinition(
        name='note.created', description='A note was created.', message='Note created'
    )
    NOTE_UPDATED: EventDefinition = EventDefinition(
        name='note.updated', description='A note was updated.', message='Note updated'
    )
    NOTE_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='note.access_updated', description='Note access was updated.', message='Note access updated'
    )
    NOTE_PINNED: EventDefinition = EventDefinition(
        name='note.pinned', description='A note was pinned.', message='Note pinned'
    )
    NOTE_UNPINNED: EventDefinition = EventDefinition(
        name='note.unpinned', description='A note was unpinned.', message='Note unpinned'
    )
    NOTE_DELETED: EventDefinition = EventDefinition(
        name='note.deleted', description='A note was deleted.', message='Note deleted'
    )
    MEMORY_CREATED: EventDefinition = EventDefinition(
        name='memory.created', description='A memory was created.', message='Memory created'
    )
    MEMORY_UPDATED: EventDefinition = EventDefinition(
        name='memory.updated', description='A memory was updated.', message='Memory updated'
    )
    MEMORY_DELETED: EventDefinition = EventDefinition(
        name='memory.deleted', description='A memory was deleted.', message='Memory deleted'
    )
    MEMORY_RESET: EventDefinition = EventDefinition(
        name='memory.reset', description='A memory was reset.', message='Memory reset'
    )
    KNOWLEDGE_CREATED: EventDefinition = EventDefinition(
        name='knowledge.created', description='A knowledge was created.', message='Knowledge created'
    )
    KNOWLEDGE_UPDATED: EventDefinition = EventDefinition(
        name='knowledge.updated', description='A knowledge was updated.', message='Knowledge updated'
    )
    KNOWLEDGE_DELETED: EventDefinition = EventDefinition(
        name='knowledge.deleted', description='A knowledge was deleted.', message='Knowledge deleted'
    )
    KNOWLEDGE_RESET: EventDefinition = EventDefinition(
        name='knowledge.reset', description='A knowledge was reset.', message='Knowledge reset'
    )
    KNOWLEDGE_REINDEXED: EventDefinition = EventDefinition(
        name='knowledge.reindexed', description='A knowledge was reindexed.', message='Knowledge reindexed'
    )
    KNOWLEDGE_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='knowledge.access_updated', description='Knowledge access was updated.', message='Knowledge access updated'
    )
    KNOWLEDGE_FILE_ADDED: EventDefinition = EventDefinition(
        name='knowledge.file.added', description='A file was added to a knowledge base.', message='Knowledge File added'
    )
    KNOWLEDGE_FILE_UPDATED: EventDefinition = EventDefinition(
        name='knowledge.file.updated', description='A knowledge file was updated.', message='Knowledge File updated'
    )
    KNOWLEDGE_FILE_REMOVED: EventDefinition = EventDefinition(
        name='knowledge.file.removed',
        description='A file was removed from a knowledge base.',
        message='Knowledge File removed',
    )
    KNOWLEDGE_FILE_MOVED: EventDefinition = EventDefinition(
        name='knowledge.file.moved', description='A knowledge file was moved.', message='Knowledge File moved'
    )
    KNOWLEDGE_DIRECTORY_CREATED: EventDefinition = EventDefinition(
        name='knowledge.directory.created',
        description='A knowledge directory was created.',
        message='Knowledge Directory created',
    )
    KNOWLEDGE_DIRECTORY_UPDATED: EventDefinition = EventDefinition(
        name='knowledge.directory.updated',
        description='A knowledge directory was updated.',
        message='Knowledge Directory updated',
    )
    KNOWLEDGE_DIRECTORY_DELETED: EventDefinition = EventDefinition(
        name='knowledge.directory.deleted',
        description='A knowledge directory was deleted.',
        message='Knowledge Directory deleted',
    )
    KNOWLEDGE_EXTERNAL_CONNECTION_CREATED: EventDefinition = EventDefinition(
        name='knowledge.external_connection.created',
        description='A knowledge external connection was created.',
        message='Knowledge External Connection created',
    )
    KNOWLEDGE_EXTERNAL_CONNECTION_UPDATED: EventDefinition = EventDefinition(
        name='knowledge.external_connection.updated',
        description='A knowledge external connection was updated.',
        message='Knowledge External Connection updated',
    )
    KNOWLEDGE_EXTERNAL_CONNECTION_DELETED: EventDefinition = EventDefinition(
        name='knowledge.external_connection.deleted',
        description='A knowledge external connection was deleted.',
        message='Knowledge External Connection deleted',
    )
    RETRIEVAL_CONTENT_PROCESSED: EventDefinition = EventDefinition(
        name='retrieval.content.processed',
        description='Retrieval content was processed.',
        message='Retrieval Content processed',
    )
    RETRIEVAL_COLLECTION_DELETED: EventDefinition = EventDefinition(
        name='retrieval.collection.deleted',
        description='A retrieval collection was deleted.',
        message='Retrieval Collection deleted',
    )
    RETRIEVAL_VECTOR_DB_RESET: EventDefinition = EventDefinition(
        name='retrieval.vector_db.reset',
        description='The retrieval vector database was reset.',
        message='Retrieval Vector Db reset',
    )
    RETRIEVAL_UPLOADS_RESET: EventDefinition = EventDefinition(
        name='retrieval.uploads.reset', description='Retrieval uploads were reset.', message='Retrieval Uploads reset'
    )
    MODEL_CREATED: EventDefinition = EventDefinition(
        name='model.created', description='A model was created.', message='Model created'
    )
    MODEL_IMPORTED: EventDefinition = EventDefinition(
        name='model.imported', description='A model was imported.', message='Model imported'
    )
    MODEL_SYNCED: EventDefinition = EventDefinition(
        name='model.synced', description='A model was synced.', message='Model synced'
    )
    MODEL_UPDATED: EventDefinition = EventDefinition(
        name='model.updated', description='A model was updated.', message='Model updated'
    )
    MODEL_DELETED: EventDefinition = EventDefinition(
        name='model.deleted', description='A model was deleted.', message='Model deleted'
    )
    MODEL_ENABLED: EventDefinition = EventDefinition(
        name='model.enabled', description='A model was enabled.', message='Model enabled'
    )
    MODEL_DISABLED: EventDefinition = EventDefinition(
        name='model.disabled', description='A model was disabled.', message='Model disabled'
    )
    MODEL_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='model.access_updated', description='Model access was updated.', message='Model access updated'
    )
    MODEL_PROVIDER_CONFIG_UPDATED: EventDefinition = EventDefinition(
        name='model.provider_config.updated',
        description='Model provider configuration was updated.',
        message='Model Provider Config updated',
    )
    MODEL_PROVIDER_MODEL_CREATED: EventDefinition = EventDefinition(
        name='model.provider_model.created',
        description='A provider model was created.',
        message='Provider model created',
    )
    MODEL_PROVIDER_MODEL_DELETED: EventDefinition = EventDefinition(
        name='model.provider_model.deleted',
        description='A provider model was deleted.',
        message='Provider model deleted',
    )
    FUNCTION_CREATED: EventDefinition = EventDefinition(
        name='function.created', description='A function was created.', message='Function created'
    )
    FUNCTION_UPDATED: EventDefinition = EventDefinition(
        name='function.updated', description='A function was updated.', message='Function updated'
    )
    FUNCTION_DELETED: EventDefinition = EventDefinition(
        name='function.deleted', description='A function was deleted.', message='Function deleted'
    )
    FUNCTION_ENABLED: EventDefinition = EventDefinition(
        name='function.enabled', description='A function was enabled.', message='Function enabled'
    )
    FUNCTION_DISABLED: EventDefinition = EventDefinition(
        name='function.disabled', description='A function was disabled.', message='Function disabled'
    )
    FUNCTION_VALVES_UPDATED: EventDefinition = EventDefinition(
        name='function.valves_updated', description='Function valves were updated.', message='Function valves updated'
    )
    TOOL_CREATED: EventDefinition = EventDefinition(
        name='tool.created', description='A tool was created.', message='Tool created'
    )
    TOOL_UPDATED: EventDefinition = EventDefinition(
        name='tool.updated', description='A tool was updated.', message='Tool updated'
    )
    TOOL_DELETED: EventDefinition = EventDefinition(
        name='tool.deleted', description='A tool was deleted.', message='Tool deleted'
    )
    TOOL_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='tool.access_updated', description='Tool access was updated.', message='Tool access updated'
    )
    TOOL_VALVES_UPDATED: EventDefinition = EventDefinition(
        name='tool.valves_updated', description='Tool valves were updated.', message='Tool valves updated'
    )
    SKILL_CREATED: EventDefinition = EventDefinition(
        name='skill.created', description='A skill was created.', message='Skill created'
    )
    SKILL_UPDATED: EventDefinition = EventDefinition(
        name='skill.updated', description='A skill was updated.', message='Skill updated'
    )
    SKILL_DELETED: EventDefinition = EventDefinition(
        name='skill.deleted', description='A skill was deleted.', message='Skill deleted'
    )
    SKILL_ENABLED: EventDefinition = EventDefinition(
        name='skill.enabled', description='A skill was enabled.', message='Skill enabled'
    )
    SKILL_DISABLED: EventDefinition = EventDefinition(
        name='skill.disabled', description='A skill was disabled.', message='Skill disabled'
    )
    PROMPT_CREATED: EventDefinition = EventDefinition(
        name='prompt.created', description='A prompt was created.', message='Prompt created'
    )
    PROMPT_UPDATED: EventDefinition = EventDefinition(
        name='prompt.updated', description='A prompt was updated.', message='Prompt updated'
    )
    PROMPT_DELETED: EventDefinition = EventDefinition(
        name='prompt.deleted', description='A prompt was deleted.', message='Prompt deleted'
    )
    PROMPT_ENABLED: EventDefinition = EventDefinition(
        name='prompt.enabled', description='A prompt was enabled.', message='Prompt enabled'
    )
    PROMPT_DISABLED: EventDefinition = EventDefinition(
        name='prompt.disabled', description='A prompt was disabled.', message='Prompt disabled'
    )
    PROMPT_VERSION_UPDATED: EventDefinition = EventDefinition(
        name='prompt.version_updated', description='A prompt version was updated.', message='Prompt version updated'
    )
    PROMPT_ACCESS_UPDATED: EventDefinition = EventDefinition(
        name='prompt.access_updated', description='Prompt access was updated.', message='Prompt access updated'
    )
    PIPELINE_UPLOADED: EventDefinition = EventDefinition(
        name='pipeline.uploaded', description='A pipeline was uploaded.', message='Pipeline uploaded'
    )
    PIPELINE_ADDED: EventDefinition = EventDefinition(
        name='pipeline.added', description='A pipeline was added.', message='Pipeline added'
    )
    PIPELINE_DELETED: EventDefinition = EventDefinition(
        name='pipeline.deleted', description='A pipeline was deleted.', message='Pipeline deleted'
    )
    PIPELINE_VALVES_UPDATED: EventDefinition = EventDefinition(
        name='pipeline.valves_updated', description='Pipeline valves were updated.', message='Pipeline valves updated'
    )
    CALENDAR_CREATED: EventDefinition = EventDefinition(
        name='calendar.created', description='A calendar was created.', message='Calendar created'
    )
    CALENDAR_UPDATED: EventDefinition = EventDefinition(
        name='calendar.updated', description='A calendar was updated.', message='Calendar updated'
    )
    CALENDAR_DELETED: EventDefinition = EventDefinition(
        name='calendar.deleted', description='A calendar was deleted.', message='Calendar deleted'
    )
    CALENDAR_DEFAULT_UPDATED: EventDefinition = EventDefinition(
        name='calendar.default_updated',
        description='The default calendar was updated.',
        message='Calendar default updated',
    )
    CALENDAR_EVENT_CREATED: EventDefinition = EventDefinition(
        name='calendar.event.created', description='A calendar event was created.', message='Calendar Event created'
    )
    CALENDAR_EVENT_UPDATED: EventDefinition = EventDefinition(
        name='calendar.event.updated', description='A calendar event was updated.', message='Calendar Event updated'
    )
    CALENDAR_EVENT_DELETED: EventDefinition = EventDefinition(
        name='calendar.event.deleted', description='A calendar event was deleted.', message='Calendar Event deleted'
    )
    CALENDAR_EVENT_RSVP_UPDATED: EventDefinition = EventDefinition(
        name='calendar.event.rsvp_updated',
        description='A calendar event RSVP was updated.',
        message='Calendar Event rsvp updated',
    )
    AUTOMATION_CREATED: EventDefinition = EventDefinition(
        name='automation.created', description='An automation was created.', message='Automation created'
    )
    AUTOMATION_UPDATED: EventDefinition = EventDefinition(
        name='automation.updated', description='An automation was updated.', message='Automation updated'
    )
    AUTOMATION_ENABLED: EventDefinition = EventDefinition(
        name='automation.enabled', description='An automation was enabled.', message='Automation enabled'
    )
    AUTOMATION_DISABLED: EventDefinition = EventDefinition(
        name='automation.disabled', description='An automation was disabled.', message='Automation disabled'
    )
    AUTOMATION_DELETED: EventDefinition = EventDefinition(
        name='automation.deleted', description='An automation was deleted.', message='Automation deleted'
    )
    AUTOMATION_RUN_STARTED: EventDefinition = EventDefinition(
        name='automation.run_started', description='An automation run started.', message='Automation run started'
    )
    AUTOMATION_RUN_COMPLETED: EventDefinition = EventDefinition(
        name='automation.run_completed', description='An automation run completed.', message='Automation run completed'
    )
    AUTOMATION_RUN_FAILED: EventDefinition = EventDefinition(
        name='automation.run_failed', description='An automation run failed.', message='Automation run failed'
    )
    FEEDBACK_CREATED: EventDefinition = EventDefinition(
        name='feedback.created', description='A feedback was created.', message='Feedback created'
    )
    FEEDBACK_UPDATED: EventDefinition = EventDefinition(
        name='feedback.updated', description='A feedback was updated.', message='Feedback updated'
    )
    FEEDBACK_DELETED: EventDefinition = EventDefinition(
        name='feedback.deleted', description='A feedback was deleted.', message='Feedback deleted'
    )
    FEEDBACK_DELETED_ALL: EventDefinition = EventDefinition(
        name='feedback.deleted_all', description='All feedback for a scope was deleted.', message='Feedback deleted all'
    )
    IMAGE_GENERATED: EventDefinition = EventDefinition(
        name='image.generated', description='An image was generated.', message='Image generated'
    )
    IMAGE_EDITED: EventDefinition = EventDefinition(
        name='image.edited', description='An image was edited.', message='Image edited'
    )
    AUDIO_SPEECH_REQUESTED: EventDefinition = EventDefinition(
        name='audio.speech_requested', description='Speech generation was requested.', message='Speech requested'
    )
    AUDIO_TRANSCRIPTION_REQUESTED: EventDefinition = EventDefinition(
        name='audio.transcription_requested',
        description='Audio transcription was requested.',
        message='Transcription requested',
    )
    TERMINAL_SESSION_OPENED: EventDefinition = EventDefinition(
        name='terminal.session.opened', description='A terminal session was opened.', message='Terminal Session opened'
    )
    TERMINAL_SESSION_CLOSED: EventDefinition = EventDefinition(
        name='terminal.session.closed', description='A terminal session was closed.', message='Terminal Session closed'
    )


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
        return not user_ids
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
        user_group_ids = {user_id: {group.id for group in groups} for user_id, groups in groups_by_user.items()}

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
            await post_webhook(
                name,
                webhook['url'],
                message,
                event.model_dump(),
                description=definition.description if definition else None,
            )
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
            params = {key: value for key, value in extra_params.items() if accepts_kwargs or key in sig.parameters}

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
