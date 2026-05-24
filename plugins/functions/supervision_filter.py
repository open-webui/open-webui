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
3. Click the gear icon and fill in the Valves. Required:
     workbench_base_url    https://workbench.example.com
     workbench_token       stw_<public>.<secret>   (mint via /admin/api_tokens)
     agent_name            openwebui_chat           (must match AgentConfig.agent_name)
   Optional (defaults usually fine):
     enabled               true                     (master kill switch)
     event_type            chat.message_completed   (sent as a top-level field; Workbench stashes it under metadata.event_type)
     timeout_seconds       3.0                      (HTTP timeout for the background POST)
     max_inflight          32                       (cap on concurrent background POSTs; over-cap events are dropped with a warning)
4. Toggle the function ON.

Endpoint contract: POST <workbench_base_url>/v1/supervision_events
See: https://github.com/swept-ai/swept-workbench/blob/main/docs/SUPERVISION_EVENTS.md
"""

import asyncio
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
            default_factory=lambda: os.getenv('WORKBENCH_AGENT_NAME', 'openwebui_chat'),
            description=(
                'Identifies this product in Workbench. Must match the AgentConfig.agent_name '
                'used for the egress callback registration.'
            ),
        )
        event_type: str = Field(
            default='chat.message_completed',
            description=(
                'Free-form tag sent as a top-level `event_type` field in the '
                'POST body; Workbench stashes it under `metadata.event_type` '
                'on the SupervisionEvent.'
            ),
        )
        timeout_seconds: float = Field(
            default=3.0,
            description='HTTP timeout for the fire-and-forget POST. Chat is never blocked by this.',
        )
        max_inflight: int = Field(
            default=32,
            description=(
                'Cap on background supervision POSTs in flight at once. '
                'If Workbench is slow/unreachable under heavy chat traffic, '
                'further events are dropped (with a warning log) instead of '
                'queueing unboundedly and eating memory + sockets.'
            ),
        )

    def __init__(self):
        self.valves = self.Valves()
        # Set is class-instance scoped, not class-scoped — each Filter
        # instance the host creates gets its own cap, which is the right
        # boundary because valves are also per-instance.
        self._inflight: set['asyncio.Task'] = set()
        # Lazily created on first send; reused across events so we get
        # keep-alive + TLS-session reuse instead of paying for a fresh
        # AsyncClient (and handshake) every chat turn. The client is
        # bound to the event loop running when it's first instantiated,
        # which is the FastAPI app loop — fine for the lifetime of the
        # process. Never explicitly closed; httpx releases sockets when
        # the loop tears down.
        self._client: Optional['httpx.AsyncClient'] = None
        self._client_lock: Optional['asyncio.Lock'] = None

    async def _get_client(self) -> 'httpx.AsyncClient':
        # Double-checked init under a lock so concurrent first calls
        # don't each create a client and race the assignment.
        if self._client is not None:
            return self._client
        if self._client_lock is None:
            self._client_lock = asyncio.Lock()
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.valves.timeout_seconds)
        return self._client

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Always return body untouched. The chat must not break if we fail.
        if not self.valves.enabled:
            return body
        if not (self.valves.workbench_base_url and self.valves.workbench_token):
            return body

        # Bounded fire-and-forget: cap the number of concurrent background
        # POSTs so a slow/unreachable Workbench can't accumulate unbounded
        # tasks under chat traffic. Drop with a warning when full instead
        # of awaiting (which would defeat the whole point of backgrounding).
        if len(self._inflight) >= self.valves.max_inflight:
            log.warning(
                '[swept_supervision] dropping event — %d background sends already in flight (max=%d)',
                len(self._inflight),
                self.valves.max_inflight,
            )
            return body

        # Schedule the send on the event loop instead of awaiting it inline.
        # `outlet` runs after the assistant response is generated but before
        # it streams back to the client; awaiting an HTTP POST here would add
        # up to `timeout_seconds` of latency to every chat. Fire-and-forget
        # via a task keeps the response path snappy and matches the docs.
        try:
            task = asyncio.create_task(self._send_event_safely(body, __user__))
            self._inflight.add(task)
            # Discard the task from the in-flight set when it finishes so
            # the cap reflects actual live work, not historical issuance.
            task.add_done_callback(self._inflight.discard)
            task.add_done_callback(self._log_task_exception)
        except RuntimeError as exc:
            # No running loop (shouldn't happen in FastAPI's request context,
            # but degrade gracefully if it does).
            log.warning('[swept_supervision] could not schedule send: %s', exc)

        return body

    async def _send_event_safely(self, body: dict, user: Optional[dict]) -> None:
        try:
            await self._send_event(body, user)
        except Exception as exc:  # noqa: BLE001 — fire-and-forget; log and move on
            log.warning('[swept_supervision] outlet send failed: %s: %s', type(exc).__name__, exc)

    @staticmethod
    def _log_task_exception(task: 'asyncio.Task') -> None:
        # asyncio.Task swallows exceptions unless someone awaits or inspects
        # them. We already wrap _send_event in try/except above, but this is
        # belt-and-suspenders so we never lose visibility on a programming bug.
        exc = task.exception() if not task.cancelled() else None
        if exc:
            log.warning('[swept_supervision] background task crashed: %s: %s', type(exc).__name__, exc)

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

        url = f'{self.valves.workbench_base_url.rstrip("/")}/v1/supervision_events'
        headers = {
            'Authorization': f'Bearer {self.valves.workbench_token}',
            'Content-Type': 'application/json',
        }

        client = await self._get_client()
        response = await client.post(
            url,
            headers=headers,
            content=json.dumps(payload),
            timeout=self.valves.timeout_seconds,
        )
        # 2xx is the only success path. Treat 3xx as a misconfiguration
        # (Workbench API endpoints don't redirect; a 3xx means the
        # base URL points at a redirector and the event was dropped) and
        # log it loudly so operators notice — same for 4xx/5xx.
        if response.status_code >= 300:
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
