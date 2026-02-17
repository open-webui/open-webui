"""
title: HRMS MCP Authentication Tool
author: open-webui
version: 0.1.0
description: Persistent per-user authentication for HRMS MCP server with SSO login flow and manual token fallback.
"""

import json
import os
import time
import uuid
import logging
import asyncio
from typing import Optional
from pathlib import Path

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

try:
    from open_webui.env import DATA_DIR
except ImportError:
    DATA_DIR = Path("/app/backend/data")

# Shared token storage file path (used by both the Tool and the callback router)
HRMS_TOKEN_FILE = Path(DATA_DIR) / "hrms_tokens.json"

# How long a pending SSO state token remains valid (seconds)
PENDING_STATE_TTL = 600  # 10 minutes


def load_hrms_data(token_file: Path = HRMS_TOKEN_FILE) -> dict:
    """Load the token/state data from the JSON file."""
    try:
        if token_file.exists():
            return json.loads(token_file.read_text())
    except Exception as e:
        log.error(f"Error loading HRMS token data: {e}")
    return {"tokens": {}, "pending_states": {}}


def save_hrms_data(data: dict, token_file: Path = HRMS_TOKEN_FILE) -> None:
    """Persist the token/state data to the JSON file."""
    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(str(token_file), 0o600)
        except OSError:
            pass
    except Exception as e:
        log.error(f"Error saving HRMS token data: {e}")


class Tools:
    class Valves(BaseModel):
        hrms_server_url: str = Field(
            default="https://hrms.example.com/mcp",
            description="Base URL of the HRMS MCP server",
        )
        sso_login_url: str = Field(
            default="https://hrms.example.com/sso/login",
            description="SSO login URL for HRMS authentication",
        )
        openwebui_base_url: str = Field(
            default="http://localhost:8080",
            description="Public base URL of this Open WebUI instance (used to build the SSO callback URL)",
        )
        sso_callback_instructions: str = Field(
            default=(
                "If the automatic redirect did not work, copy the token from the "
                "SSO callback page and paste it here using the save_hrms_token tool."
            ),
            description="Instructions shown to users when authentication is needed",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._lock = asyncio.Lock()

    # ── Private helpers ───────────────────────────────────────────────

    def _get_token(self, user_id: str) -> Optional[str]:
        """Retrieve the stored access token for a user, or None."""
        data = load_hrms_data()
        entry = data.get("tokens", {}).get(user_id)
        if entry:
            return entry.get("access_token")
        return None

    def _store_token(self, user_id: str, token: str) -> None:
        """Store an access token for a user."""
        data = load_hrms_data()
        data.setdefault("tokens", {})[user_id] = {
            "access_token": token,
            "saved_at": int(time.time()),
        }
        save_hrms_data(data)

    def _delete_token(self, user_id: str) -> None:
        """Delete the stored token for a user."""
        data = load_hrms_data()
        if user_id in data.get("tokens", {}):
            del data["tokens"][user_id]
            save_hrms_data(data)

    def _create_pending_state(self, user_id: str) -> str:
        """Create a short-lived state token that maps back to a user_id."""
        state = uuid.uuid4().hex
        data = load_hrms_data()
        data.setdefault("pending_states", {})[state] = {
            "user_id": user_id,
            "created_at": int(time.time()),
        }
        save_hrms_data(data)
        return state

    def _build_sso_url(self, user_id: str) -> str:
        """Construct the full SSO login URL including redirect and state params."""
        state = self._create_pending_state(user_id)
        callback_url = (
            f"{self.valves.openwebui_base_url.rstrip('/')}/api/v1/hrms/callback"
        )
        sso_base = self.valves.sso_login_url.rstrip("/")
        separator = "&" if "?" in sso_base else "?"
        return f"{sso_base}{separator}redirect={callback_url}&state={state}"

    def _auth_required_response(self, sso_url: str) -> str:
        return json.dumps(
            {
                "error": "authentication_required",
                "sso_login_url": sso_url,
                "instructions": self.valves.sso_callback_instructions,
                "message": (
                    f"You are not authenticated with HRMS. "
                    f"Please visit the following link to log in: {sso_url} "
                    f"— {self.valves.sso_callback_instructions}"
                ),
            }
        )

    def _token_expired_response(self, sso_url: str) -> str:
        return json.dumps(
            {
                "error": "token_expired",
                "sso_login_url": sso_url,
                "instructions": self.valves.sso_callback_instructions,
                "message": (
                    f"Your HRMS session has expired. "
                    f"Please visit the following link to re-authenticate: {sso_url} "
                    f"— {self.valves.sso_callback_instructions}"
                ),
            }
        )

    # ── Public tool methods (exposed to the LLM) ─────────────────────

    async def check_hrms_auth(
        self,
        __user__: dict = {},
        __event_emitter__: callable = None,
    ) -> str:
        """
        Check if you are currently authenticated with the HRMS system.
        Returns authentication status and login instructions if needed.

        :return: JSON with authentication status
        """
        user_id = __user__.get("id", "")
        token = self._get_token(user_id)

        if token:
            return json.dumps(
                {
                    "authenticated": True,
                    "message": "You are authenticated with HRMS.",
                }
            )
        else:
            sso_url = self._build_sso_url(user_id)
            return self._auth_required_response(sso_url)

    async def save_hrms_token(
        self,
        token: str,
        __user__: dict = {},
        __event_emitter__: callable = None,
    ) -> str:
        """
        Manually save your HRMS authentication token after SSO login.
        Use this if the automatic redirect did not capture your token.

        :param token: The Bearer token obtained from SSO login
        :return: JSON confirming the token was saved
        """
        user_id = __user__.get("id", "")
        if not token or not token.strip():
            return json.dumps({"error": "Token cannot be empty."})

        token = token.strip()

        async with self._lock:
            self._store_token(user_id, token)

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "hrms_auth",
                        "description": "HRMS token saved successfully.",
                        "done": True,
                    },
                }
            )

        return json.dumps(
            {
                "status": "success",
                "message": "HRMS token saved. You can now use HRMS tools.",
            }
        )

    async def call_hrms_tool(
        self,
        tool_name: str,
        arguments: str = "{}",
        __user__: dict = {},
        __event_emitter__: callable = None,
    ) -> str:
        """
        Call an HRMS tool on the MCP server by name.
        Handles authentication automatically — if you are not logged in,
        you will receive a login link.

        :param tool_name: Name of the HRMS tool to call (e.g. get_salary, get_leave_balance)
        :param arguments: JSON string of arguments for the tool
        :return: JSON result from the HRMS server
        """
        from open_webui.utils.mcp.client import MCPClient

        user_id = __user__.get("id", "")
        token = self._get_token(user_id)

        if not token:
            sso_url = self._build_sso_url(user_id)
            return self._auth_required_response(sso_url)

        # Parse arguments
        try:
            args_dict = (
                json.loads(arguments) if isinstance(arguments, str) else arguments
            )
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in arguments parameter."})

        # Emit progress status
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "hrms_call",
                        "description": f"Calling HRMS: {tool_name}...",
                        "done": False,
                    },
                }
            )

        headers = {
            "Authorization": f"Bearer {token}",
        }

        client = MCPClient()
        try:
            await client.connect(
                url=self.valves.hrms_server_url,
                headers=headers,
            )
            result = await client.call_tool(tool_name, args_dict)

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "action": "hrms_call",
                            "description": "HRMS call complete.",
                            "done": True,
                        },
                    }
                )

            return json.dumps(result) if isinstance(result, (dict, list)) else str(result)

        except Exception as e:
            error_msg = str(e)
            # Detect authentication failures
            if "401" in error_msg or "nauthorized" in error_msg:
                async with self._lock:
                    self._delete_token(user_id)

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "action": "hrms_auth",
                                "description": "HRMS authentication expired.",
                                "done": True,
                            },
                        }
                    )

                sso_url = self._build_sso_url(user_id)
                return self._token_expired_response(sso_url)

            log.exception(f"HRMS tool call failed: {e}")
            return json.dumps({"error": f"HRMS call failed: {error_msg}"})

        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
