"""Per-user credentials for admin-defined tool server connections.

The connection itself stays admin-owned; only the values a user fills in for the
slots the admin declared live here. They are kept in
``user.settings['tool_servers']['user_config'][<server_id>]`` and go through the
same helper that stores tool and function valves, which means they are encrypted
at rest only when ``ENABLE_VALVE_ENCRYPTION`` is enabled — it is off by default,
and these values are then stored as submitted, exactly like valves are.
"""

from __future__ import annotations

import logging

from open_webui.models.users import Users
from open_webui.utils.valves import decrypt_valves, encrypt_valves
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def get_user_configs_from_settings(settings) -> dict:
    """Return the raw (possibly encrypted) per-connection configs held in user settings."""
    if settings is None:
        return {}
    if not isinstance(settings, dict):
        settings = settings.model_dump()
    return (settings.get('tool_servers') or {}).get('user_config') or {}


def settings_without_user_configs(settings) -> dict | None:
    """Settings with the per-user tool server credentials removed.

    Credentials are only ever written through the dedicated endpoints and read on
    the request path, so they have no reason to travel back out with the rest of
    the settings blob.
    """
    if settings is None:
        return None
    if not isinstance(settings, dict):
        settings = settings.model_dump()
    if 'tool_servers' not in settings:
        return settings

    tool_servers = {key: value for key, value in (settings.get('tool_servers') or {}).items() if key != 'user_config'}
    return (
        {**settings, 'tool_servers': tool_servers}
        if tool_servers
        else {key: value for key, value in settings.items() if key != 'tool_servers'}
    )


class ToolServerUserConfigsTable:
    async def get_config(self, server_id: str, user_id: str, db: AsyncSession | None = None) -> dict:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            return decrypt_valves(get_user_configs_from_settings(user.settings if user else None).get(server_id))
        except Exception:
            log.exception(f'Error getting user config for tool server {server_id} and user_id {user_id}')
            return {}

    async def update_config(
        self, server_id: str, user_id: str, values: dict, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            settings = user.settings.model_dump() if user and user.settings else {}

            tool_servers = settings.get('tool_servers') or {}
            user_config = tool_servers.get('user_config') or {}
            user_config[server_id] = encrypt_valves(values)
            tool_servers['user_config'] = user_config
            settings['tool_servers'] = tool_servers

            await Users.update_user_by_id(user_id, {'settings': settings}, db=db)
            return values
        except Exception:
            log.exception(f'Error updating user config for tool server {server_id} and user_id {user_id}')
            return None

    async def delete_config(self, server_id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            settings = user.settings.model_dump() if user and user.settings else {}

            tool_servers = settings.get('tool_servers') or {}
            user_config = tool_servers.get('user_config') or {}
            user_config.pop(server_id, None)
            tool_servers['user_config'] = user_config
            settings['tool_servers'] = tool_servers

            await Users.update_user_by_id(user_id, {'settings': settings}, db=db)
            return True
        except Exception:
            log.exception(f'Error deleting user config for tool server {server_id} and user_id {user_id}')
            return False


ToolServerUserConfigs = ToolServerUserConfigsTable()  # singleton accessor
