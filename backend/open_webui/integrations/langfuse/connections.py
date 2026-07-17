from __future__ import annotations

import base64
from typing import Any

from open_webui.models.config import Config


def langfuse_basic_auth_header(public_key: str, secret_key: str) -> dict[str, str]:
    token = base64.b64encode(f'{public_key}:{secret_key}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


def merge_langfuse_connection_secrets(
    incoming: list[dict],
    existing: list[dict] | None,
) -> list[dict]:
    """Preserve stored secret_key when the client omits it on update."""
    existing_by_id = {c.get('id'): c for c in (existing or []) if c.get('id')}
    merged: list[dict] = []

    for connection in incoming:
        updated = dict(connection)
        conn_id = updated.get('id')
        if not updated.get('secret_key') and conn_id and conn_id in existing_by_id:
            updated['secret_key'] = existing_by_id[conn_id].get('secret_key', '')
        merged.append(updated)

    return merged


async def get_langfuse_connections_with_secrets() -> list[dict[str, Any]]:
    """Load Langfuse connections from Config, including secret keys."""
    return list(await Config.get('langfuse.connections') or [])


async def get_connection_by_id(connection_id: str) -> dict[str, Any] | None:
    """Return a Langfuse connection by id, or None if not found."""
    if not connection_id:
        return None
    return next(
        (
            connection
            for connection in await get_langfuse_connections_with_secrets()
            if connection.get('id') == connection_id
        ),
        None,
    )


async def list_enabled_connections() -> list[dict[str, Any]]:
    """Return enabled Langfuse connections with secrets (for server-side API calls)."""
    return [
        connection for connection in await get_langfuse_connections_with_secrets() if connection.get('enabled', True)
    ]


def redact_langfuse_connections_for_response(connections: list[dict] | None) -> list[dict]:
    """Return connections without echoing secret_key values."""
    redacted: list[dict] = []
    for connection in connections or []:
        item = dict(connection)
        secret = item.get('secret_key')
        item['secret_key'] = ''
        item['secret_key_set'] = bool(secret)
        redacted.append(item)
    return redacted
