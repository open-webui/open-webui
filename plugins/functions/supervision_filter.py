"""
title: Swept Workbench Supervision
author: pioneer-chat
author_url: https://github.com/swept-ai/open-webui
version: 0.1.0
license: MIT
required_open_webui_version: 0.5.0
requirements: httpx>=0.25.0

Filter that forwards each user/assistant exchange to a Swept Workbench
instance for supervision evaluation. Fires from the `outlet` lifecycle
hook — after the assistant has responded but before the response is
streamed back. Failures are logged and swallowed; the chat must never
break because Workbench is unreachable.

Install
-------
1. Admin Panel > Functions > "+" (top right).
2. Paste this file's contents. Save.
3. Click the gear icon and fill in the four Valves:
     workbench_base_url    https://workbench.example.com
     workbench_token       stw_<public>.<secret>   (mint via /admin/api_tokens)
     agent_name            chat_phoenix             (must match AgentConfig.agent_name)
     enabled               true
4. Toggle the function ON.

Endpoint contract: POST <workbench_base_url>/v1/supervision_events
See: https://github.com/swept-ai/swept-workbench/blob/main/docs/SUPERVISION_EVENTS.md
"""

import json
import logging
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class Filter:
    class Valves(BaseModel):
        enabled: bool = Field(
            default=True,
            description='Master switch. Set false to stop sending events without uninstalling.',
        )
        workbench_base_url: str = Field(
            default_factory=lambda: os.getenv('WORKBENCH_BASE_URL', ''),
            description='Base URL of the Workbench instance (no trailing slash).',
        )
        workbench_token: str = Field(
            default_factory=lambda: os.getenv('WORKBENCH_API_TOKEN', ''),
            description='Bearer token minted via /admin/api_tokens. Format: stw_<public>.<secret>',
        )
        agent_name: str = Field(
            default_factory=lambda: os.getenv('WORKBENCH_AGENT_NAME', 'chat_phoenix'),
            description=(
                'Identifies this product in Workbench. Must match the AgentConfig.agent_name '
                'used for the egress callback registration.'
            ),
        )
        event_type: str = Field(
            default='chat.message_completed',
            description='Free-form tag. Stashed in metadata.event_type.',
        )
        timeout_seconds: float = Field(
            default=3.0,
            description='HTTP timeout for the fire-and-forget POST. Chat is never blocked by this.',
        )

    def __init__(self):
        self.valves = self.Valves()

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Always return body untouched. The chat must not break if we fail.
        if not self.valves.enabled:
            return body
        if not (self.valves.workbench_base_url and self.valves.workbench_token):
            return body

        try:
            await self._send_event(body, __user__)
        except Exception as exc:  # noqa: BLE001 — fire-and-forget; log and move on
            log.warning('[swept_supervision] outlet send failed: %s: %s', type(exc).__name__, exc)

        return body

    async def _send_event(self, body: dict, user: Optional[dict]) -> None:
        user_message, agent_response, last_message_id = self._extract_pair(body)
        if not (user_message and agent_response):
            # Incomplete exchange — nothing meaningful to supervise.
            return

        payload = {
            'event_type': self.valves.event_type,
            'agent_name': self.valves.agent_name,
            'data': {
                'user_message': user_message,
                'agent_response': agent_response,
                'message_id': body.get('id') or last_message_id,
                'chat_id': body.get('chat_id') or body.get('chat', {}).get('id'),
                'model': body.get('model'),
                'user_email': (user or {}).get('email'),
            },
        }

        url = f"{self.valves.workbench_base_url.rstrip('/')}/v1/supervision_events"
        headers = {
            'Authorization': f'Bearer {self.valves.workbench_token}',
            'Content-Type': 'application/json',
        }

        async with httpx.AsyncClient(timeout=self.valves.timeout_seconds) as client:
            response = await client.post(url, headers=headers, content=json.dumps(payload))
            if response.status_code >= 400:
                log.warning(
                    '[swept_supervision] workbench %s on POST /v1/supervision_events: %s',
                    response.status_code,
                    response.text[:200],
                )

    @staticmethod
    def _extract_pair(body: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Pull the most recent user message and the assistant response from body.messages."""
        messages = body.get('messages') or []
        user_msg: Optional[str] = None
        agent_msg: Optional[str] = None
        last_message_id: Optional[str] = None

        for message in reversed(messages):
            role = message.get('role')
            content = message.get('content', '')
            if isinstance(content, list):
                # OpenAI-style content blocks; concatenate text parts.
                content = ''.join(
                    block.get('text', '')
                    for block in content
                    if isinstance(block, dict) and block.get('type') in ('text', None)
                )
            if role == 'assistant' and agent_msg is None:
                agent_msg = content
                last_message_id = last_message_id or message.get('id')
            elif role == 'user' and user_msg is None:
                user_msg = content
            if user_msg and agent_msg:
                break

        return user_msg, agent_msg, last_message_id
