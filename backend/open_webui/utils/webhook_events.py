"""
Webhook Event Types and Constants

This module defines the available event types for webhook triggers
and provides utilities for event handling.
"""

from enum import Enum
from typing import Dict, Any, List


class WebhookEvent(Enum):
    """Available webhook event types"""

    # Authentication Events
    USER_SIGNUP = "auth.user.signup"
    USER_LOGIN = "auth.user.login"
    USER_LOGOUT = "auth.user.logout"
    USER_PASSWORD_CHANGE = "auth.user.password_change"

    # Chat Events
    CHAT_CREATED = "chat.created"
    CHAT_UPDATED = "chat.updated"
    CHAT_DELETED = "chat.deleted"
    CHAT_SHARED = "chat.shared"
    MESSAGE_CREATED = "chat.message.created"

    # Channel Events
    CHANNEL_MESSAGE_CREATED = "channel.message.created"

    # Admin Events
    ADMIN_USER_CREATED = "admin.user.created"
    ADMIN_USER_UPDATED = "admin.user.updated"
    ADMIN_USER_DELETED = "admin.user.deleted"
    ADMIN_MODEL_CREATED = "admin.model.created"
    ADMIN_MODEL_UPDATED = "admin.model.updated"
    ADMIN_MODEL_DELETED = "admin.model.deleted"

    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Tool and Function Events
    FUNCTION_CREATED = "function.created"
    FUNCTION_UPDATED = "function.updated"
    FUNCTION_DELETED = "function.deleted"
    TOOL_CREATED = "tool.created"
    TOOL_UPDATED = "tool.updated"
    TOOL_DELETED = "tool.deleted"

    # Knowledge Events
    KNOWLEDGE_CREATED = "knowledge.created"
    KNOWLEDGE_UPDATED = "knowledge.updated"
    KNOWLEDGE_DELETED = "knowledge.deleted"


# Event metadata - describes what data each event provides
EVENT_METADATA: Dict[str, Dict[str, Any]] = {
    WebhookEvent.USER_SIGNUP.value: {
        "description": "Triggered when a new user signs up",
        "data_fields": ["user_id", "name", "email", "role", "created_at"],
    },
    WebhookEvent.USER_LOGIN.value: {
        "description": "Triggered when a user logs in",
        "data_fields": ["user_id", "name", "email", "login_at", "ip_address"],
    },
    WebhookEvent.USER_LOGOUT.value: {
        "description": "Triggered when a user logs out",
        "data_fields": ["user_id", "name", "logout_at"],
    },
    WebhookEvent.USER_PASSWORD_CHANGE.value: {
        "description": "Triggered when a user changes their password",
        "data_fields": ["user_id", "name", "changed_at"],
    },
    WebhookEvent.CHAT_CREATED.value: {
        "description": "Triggered when a new chat is created",
        "data_fields": ["chat_id", "user_id", "title", "model", "created_at"],
    },
    WebhookEvent.CHAT_UPDATED.value: {
        "description": "Triggered when a chat is updated",
        "data_fields": ["chat_id", "user_id", "title", "updated_at"],
    },
    WebhookEvent.CHAT_DELETED.value: {
        "description": "Triggered when a chat is deleted",
        "data_fields": ["chat_id", "user_id", "deleted_at"],
    },
    WebhookEvent.CHAT_SHARED.value: {
        "description": "Triggered when a chat is shared",
        "data_fields": ["chat_id", "user_id", "share_id", "shared_at"],
    },
    WebhookEvent.MESSAGE_CREATED.value: {
        "description": "Triggered when a new message is created in a chat",
        "data_fields": [
            "chat_id",
            "user_id",
            "message_id",
            "role",
            "content_preview",
            "created_at",
        ],
    },
    WebhookEvent.CHANNEL_MESSAGE_CREATED.value: {
        "description": "Triggered when a new message is created in a channel",
        "data_fields": [
            "channel_id",
            "user_id",
            "message_id",
            "content_preview",
            "created_at",
        ],
    },
    WebhookEvent.ADMIN_USER_CREATED.value: {
        "description": "Triggered when an admin creates a new user",
        "data_fields": ["user_id", "name", "email", "role", "created_by", "created_at"],
    },
    WebhookEvent.ADMIN_USER_UPDATED.value: {
        "description": "Triggered when an admin updates a user",
        "data_fields": ["user_id", "name", "email", "role", "updated_by", "updated_at"],
    },
    WebhookEvent.ADMIN_USER_DELETED.value: {
        "description": "Triggered when an admin deletes a user",
        "data_fields": ["user_id", "name", "deleted_by", "deleted_at"],
    },
    WebhookEvent.SYSTEM_STARTUP.value: {
        "description": "Triggered when the system starts up",
        "data_fields": ["version", "startup_at"],
    },
    WebhookEvent.SYSTEM_SHUTDOWN.value: {
        "description": "Triggered when the system shuts down",
        "data_fields": ["version", "shutdown_at"],
    },
    WebhookEvent.SYSTEM_ERROR.value: {
        "description": "Triggered when a system error occurs",
        "data_fields": ["error_type", "error_message", "occurred_at"],
    },
}


def get_available_events() -> List[Dict[str, Any]]:
    """Get list of all available webhook events with their metadata"""
    return [
        {
            "event": event.value,
            "name": event.name,
            "description": EVENT_METADATA.get(event.value, {}).get("description", ""),
            "data_fields": EVENT_METADATA.get(event.value, {}).get("data_fields", []),
        }
        for event in WebhookEvent
    ]


def get_event_categories() -> Dict[str, List[str]]:
    """Get events organized by category"""
    categories = {}
    for event in WebhookEvent:
        category = event.value.split(".")[0]
        if category not in categories:
            categories[category] = []
        categories[category].append(event.value)
    return categories


def validate_events(events: List[str]) -> List[str]:
    """Validate that all provided events are valid event types"""
    valid_events = [event.value for event in WebhookEvent]
    return [event for event in events if event in valid_events]


def is_valid_event(event: str) -> bool:
    """Check if an event type is valid"""
    return event in [e.value for e in WebhookEvent]
