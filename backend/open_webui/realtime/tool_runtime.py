"""Realtime-owned tool resolution and execution runtime."""


import copy
import json
import logging
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass
class RealtimeToolAuthContext:
    session_token: str = ""
    oauth_session_id: str = ""


class RealtimeToolRequest:
    """Minimal request-like object for realtime tool resolution/execution.

    This intentionally carries only explicit server-owned auth state needed by
    OWUI tool handlers instead of replaying the original browser request.
    """

    def __init__(
        self,
        app: Any,
        *,
        session_token: str = "",
        oauth_session_id: str = "",
        metadata: Optional[dict] = None,
    ):
        self.app = app
        self.state = SimpleNamespace(
            token=SimpleNamespace(credentials=session_token),
            direct=False,
            metadata=metadata or {},
        )
        self.cookies = (
            {"oauth_session_id": oauth_session_id} if oauth_session_id else {}
        )
        self.headers = {}
        self.query_params = {}
        self.method = "POST"
        self.url = SimpleNamespace(path="")
        self.path_params = {}
        self.scope = {}

    def __getattr__(self, name):
        raise AttributeError(
            f"{self.__class__.__name__} has no attribute '{name}'"
        )


async def resolve_realtime_tools(
    *,
    app: Any,
    user: Any,
    model: dict,
    chat_id: str,
    session_id: str,
    tool_ids: Optional[list[str]],
    tool_servers: Optional[list[dict]],
    terminal_id: Optional[str],
    features: Optional[dict],
    auth_context: RealtimeToolAuthContext,
    event_emitter: Any = None,
    event_caller: Any = None,
) -> tuple[RealtimeToolRequest, dict[str, dict]]:
    # Import lazily to avoid a module cycle:
    # socket.main -> session_service -> tool_runtime -> middleware -> socket.main
    from open_webui.utils.middleware import process_chat_payload

    metadata = {
        "chat_id": chat_id,
        "message_id": "",
        "session_id": session_id,
        "user_id": getattr(user, "id", ""),
        "tool_ids": tool_ids or [],
        "tool_servers": copy.deepcopy(tool_servers or []),
        "terminal_id": terminal_id,
        "features": features or {},
        "params": {"function_calling": "native"},
    }
    request = RealtimeToolRequest(
        app,
        session_token=auth_context.session_token,
        oauth_session_id=auth_context.oauth_session_id,
        metadata=metadata,
    )
    request.state.metadata = metadata

    tool_form = {
        "model": model.get("id", ""),
        "messages": [],
        "tool_ids": tool_ids or [],
        "tool_servers": copy.deepcopy(tool_servers or []),
        "terminal_id": terminal_id,
        "features": features or {},
    }

    tool_form, metadata, _ = await process_chat_payload(
        request,
        tool_form,
        user,
        metadata,
        model,
    )

    return request, metadata.get("tools", {})


async def execute_realtime_tool_call(
    *,
    tool_call_id: str,
    tool_function_name: str,
    tool_args,
    tools: dict,
    request,
    user,
    metadata: dict,
    event_emitter=None,
    event_caller=None,
) -> dict:
    """Thin sideband wrapper around middleware.execute_tool_call.

    Adds realtime-specific adaptations before and after the stock call:
    - Pre-parse dict args to JSON string (defensive)
    - Guard event_caller for direct tools without browser session
    - Guard event_emitter (may be None in sideband context)
    - Track tool_failed status in the returned dict
    - Emit files/embeds events (stock inline path does not emit these)
    """
    from open_webui.utils.middleware import execute_tool_call

    # Pre-process: handle dict args (OpenAI may send pre-parsed dicts)
    if isinstance(tool_args, dict):
        tool_args = json.dumps(tool_args)
    elif not isinstance(tool_args, str):
        tool_args = '{}'

    # Pre-process: guard event_caller for direct tools
    actual_event_caller = event_caller
    if event_caller is None:
        async def _no_caller(payload):
            return json.dumps({'error': 'No browser session for direct tool'})
        actual_event_caller = _no_caller

    # Async no-op emitter so stock execute_tool_call doesn't crash
    # on await event_emitter(...) inside terminal_event_handler
    async def _noop_emitter(x):
        pass

    actual_event_emitter = event_emitter or _noop_emitter

    result = await execute_tool_call(
        tool_call_id=tool_call_id,
        tool_function_name=tool_function_name,
        tool_args=tool_args,
        tools=tools,
        request=request,
        user=user,
        metadata=metadata,
        messages=[],
        files=[],
        event_emitter=actual_event_emitter,
        event_caller=actual_event_caller,
        citations_enabled=True,
    )

    # Post-process: determine failure status
    failed = False
    content = result.get('content', '')
    if content.startswith('Error:'):
        failed = True
    if tool_function_name not in tools:
        failed = True

    result['failed'] = failed

    # Post-process: emit files/embeds events (stock path doesn't do this)
    if event_emitter:
        result_files = result.get('files')
        result_embeds = result.get('embeds')
        if result_files:
            await event_emitter(
                {'type': 'files', 'data': {'files': result_files}}
            )
        if result_embeds:
            await event_emitter(
                {'type': 'embeds', 'data': {'embeds': result_embeds}}
            )

    return result
