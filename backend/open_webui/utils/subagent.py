"""Subagent runner — orchestrates the inner chat-completion pipeline for a
research subagent spawned by the parent chat model.

Architecture, condensed:

- The parent chat's tool-call loop awaits ``subagent_launch`` /
  ``subagent_continue`` from ``utils.subagent_tool``. Those tool wrappers
  delegate here.
- ``run_subagent_launch`` creates a hidden Chat row (``meta.subagent_of`` set
  atomically so it never appears in the user's sidebar) and calls
  ``_run_inner_chat``.
- ``run_subagent_continue`` looks up an existing subagent chat by name-or-id
  and calls ``_run_inner_chat`` to drive one more turn on top of its history.
- ``_run_inner_chat`` builds inner_form_data + inner_metadata, then re-enters
  the exact same pipeline the regular chat path uses
  (``process_chat_payload`` → ``chat_completion_handler`` →
  ``process_chat_response``). The middleware's tool-call loop, reasoning
  preservation (``REASONING_DETAILS.md`` contract), filter pipelines, etc.
  all work for free because we're inside the same machinery.

Event forwarding:

- The inner pipeline emits events scoped to the subagent's chat_id; the
  parent's frontend would normally drop those (``isVisibleChatEvent``).
- We install an ``event_emitter_override`` on inner_metadata. It (a) still
  calls the default subagent emitter to persist to the subagent's chat row,
  and (b) re-emits whitelisted event types to the *parent's* emitter wrapped
  as ``{type: "chat:subagent:update", data: {subagent_id, num, name,
  parent_message_id, inner_event}}`` — which the frontend routes into the
  ``subagentLiveStates`` store and renders inside the parent message.

Nesting prevention:

- The inner ``features`` dict is empty and inner ``tool_ids`` only contain
  ``builtin:web_search`` + user-selected extras. The subagent tools are NOT
  registered for the inner run, so a subagent can't recursively spawn another.

request.state save/restore:

- ``utils/chat.generate_chat_completion`` (called by middleware's tool-call
  loop for each round AFTER the first) merges ``request.state.metadata`` over
  ``form_data["metadata"]`` (parent wins). For the subagent run we need the
  inner metadata to win, so we swap ``request.state.{metadata,model,direct}``
  for the duration of the run and restore on exit. The parent's outer
  pipeline is suspended at ``await tool_function(...)`` so no concurrent
  reader sees the swap.
"""

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from fastapi import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.chats import Chats, ChatImportForm
from open_webui.models.models import Models
from open_webui.models.users import Users
from open_webui.socket.main import get_event_call, get_event_emitter
from open_webui.utils.chat import generate_chat_completion as chat_completion_handler
from open_webui.utils.messages import blocks_to_api_messages, blocks_to_plain_text
from open_webui.utils.middleware import (
    current_tool_call_id_var,
    process_chat_payload,
    process_chat_response,
)
from open_webui.utils.misc import get_message_list

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gather_all_subagent_runs(parent_chat) -> dict:
    """Collect every ``subagent_runs`` entry across every message in the parent
    chat's history. Returns a flat ``{subagent_id: run_dict}`` map.

    This is the source-of-truth for ``run_subagent_continue`` (name/id
    resolution) and for ``run_subagent_launch`` (collision-disambiguation and
    num assignment)."""
    if not parent_chat:
        return {}
    history = (parent_chat.chat or {}).get("history") or {}
    messages = history.get("messages") or {}
    all_runs: dict = {}
    if isinstance(messages, dict):
        for msg in messages.values():
            if not isinstance(msg, dict):
                continue
            runs = msg.get("subagent_runs")
            if isinstance(runs, dict):
                all_runs.update(runs)
    return all_runs


def _disambiguate_name(name: str, all_runs: dict) -> tuple[str, bool]:
    """If ``name`` is already taken by an existing subagent in this parent
    chat, return ``("name_2", True)`` (or ``_3``, etc.). Otherwise return
    ``(name, False)``. The second tuple element tells the caller whether to
    surface a "Note: renamed to X" line in the tool result.

    Comparison is case-insensitive to catch obvious near-collisions
    (``Berkeley`` vs ``berkeley``); the disambiguator preserves the parent
    model's chosen casing on the base."""
    if not name:
        return ("subagent", False)
    existing_names_lower = {
        (run.get("name") or "").lower()
        for run in all_runs.values()
        if isinstance(run, dict)
    }
    if name.lower() not in existing_names_lower:
        return (name, False)
    n = 2
    while True:
        candidate = f"{name}_{n}"
        if candidate.lower() not in existing_names_lower:
            return (candidate, True)
        n += 1


def _resolve_subagent_model_id(
    request: Request, parent_chat, parent_model: Optional[dict]
) -> Optional[str]:
    """Resolution order: per-chat override → global default → parent model.
    Returns None if no model is resolvable or if the resolved model isn't in
    ``app.state.MODELS`` (caller surfaces an error in that case)."""
    chat_params = ((parent_chat.chat if parent_chat else {}) or {}).get("params") or {}
    candidates = [
        chat_params.get("subagentModel"),
        getattr(request.app.state.config, "SUBAGENT_DEFAULT_MODEL", None) or None,
        (parent_model or {}).get("id"),
    ]
    for cand in candidates:
        if cand and cand in request.app.state.MODELS:
            return cand
    return None


def _compose_subagent_system_prompt(request: Request, subagent_model_id: str) -> str:
    """Combine the admin-editable subagent preamble with the subagent model's
    own configured system prompt (from ``Models`` table params, if any).

    The preamble goes FIRST so its "you are a research subagent / no tool
    calls in final turn means done / no clarifying questions" instructions
    can't be drowned out by a model's verbose default prompt."""
    preamble = (
        getattr(request.app.state.config, "SUBAGENT_SYSTEM_PROMPT", "") or ""
    ).strip()
    model_system = ""
    try:
        model_info = Models.get_model_by_id(subagent_model_id)
        if model_info and model_info.params:
            params = (
                model_info.params.model_dump()
                if hasattr(model_info.params, "model_dump")
                else dict(model_info.params)
            )
            model_system = (params.get("system") or "").strip()
    except Exception as e:  # noqa: BLE001 - non-fatal; fall back to preamble alone
        log.debug(f"could not load model system prompt for {subagent_model_id}: {e}")
    if preamble and model_system:
        return f"{preamble}\n\n{model_system}"
    return preamble or model_system


def _upsert_subagent_run(
    parent_chat_id: str, parent_message_id: str, subagent_id: str, patch: dict
) -> None:
    """Merge ``patch`` into ``parent_message.subagent_runs[subagent_id]``,
    preserving other keys and sibling subagents. Idempotent — safe to call
    multiple times. Skips silently if either id is missing or the chat row is
    a temp/local chat (those never persist)."""
    if not parent_chat_id or not parent_message_id or not subagent_id:
        return
    if parent_chat_id.startswith("local:"):
        return
    try:
        existing_message = (
            Chats.get_message_by_id_and_message_id(parent_chat_id, parent_message_id)
            or {}
        )
        existing_runs = existing_message.get("subagent_runs") or {}
        if not isinstance(existing_runs, dict):
            existing_runs = {}
        prior = existing_runs.get(subagent_id) or {}
        if not isinstance(prior, dict):
            prior = {}
        merged_run = {**prior, **patch}
        new_runs = {**existing_runs, subagent_id: merged_run}
        Chats.upsert_message_to_chat_by_id_and_message_id(
            parent_chat_id, parent_message_id, {"subagent_runs": new_runs}
        )
    except Exception as e:  # noqa: BLE001
        log.warning(
            f"failed to upsert subagent_run {subagent_id} on "
            f"{parent_chat_id}/{parent_message_id}: {e}"
        )


def _build_forwarding_emitter(
    subagent_socket_info: dict,
    parent_event_emitter: Callable[[dict], Awaitable[None]],
    subagent_meta: dict,
) -> Callable[[dict], Awaitable[None]]:
    """Wraps the inner pipeline's event_emitter so each emitted event both:

    1. Goes through the subagent's own ``get_event_emitter`` (which persists
       fields like ``status``/``message``/``replace``/``files``/``sources``
       to the subagent chat row, exactly the same as a top-level chat).
    2. Is forwarded to the parent UI as ``chat:subagent:update`` so the
       parent message's collapsible block updates live.

    Only whitelisted event types are forwarded — we want content/status/error
    flow to reach the parent UI, not internal control events like cancel
    triggers (those are surfaced separately if and when they happen).
    """
    base_emitter = get_event_emitter(subagent_socket_info)

    FORWARDED_TYPES = {
        "chat:completion",
        "chat:message:error",
        "chat:message:delta",
        "status",
        "source",
        "citation",
        "chat:tasks:cancel",
    }

    async def forwarding_emitter(event: dict) -> None:
        # Always persist to subagent's chat row + emit on subagent scope first.
        # We swallow errors from the base emitter so a hiccup persisting one
        # chunk doesn't break the forward (the parent UI is the source of
        # truth for live display; the subagent row is a backup for replay).
        try:
            await base_emitter(event)
        except Exception as e:  # noqa: BLE001
            log.debug(f"subagent base emitter raised: {e}")

        if not isinstance(event, dict):
            return
        etype = event.get("type")
        if etype not in FORWARDED_TYPES:
            return
        try:
            await parent_event_emitter(
                {
                    "type": "chat:subagent:update",
                    "data": {
                        **subagent_meta,
                        "inner_event": event,
                    },
                }
            )
        except Exception as e:  # noqa: BLE001
            log.debug(f"forwarding to parent UI failed: {e}")

    return forwarding_emitter


def _append_history_for_inner_run(
    subagent_chat_id: str, prompt: str, user_msg_id: str, assistant_msg_id: str, model_id: str
) -> None:
    """Append a new user message and a blank assistant message to the
    subagent chat's history. Used both at launch (history was empty) and at
    continue (history grows by one round).

    Writes directly via ``update_chat_by_id`` so the two messages land in a
    single row update — atomic w.r.t. the next save."""
    chat = Chats.get_chat_by_id(subagent_chat_id)
    if not chat:
        raise RuntimeError(f"subagent chat {subagent_chat_id} not found")
    chat_data = chat.chat or {}
    history = chat_data.get("history") or {}
    messages = history.get("messages") or {}
    prev_id = history.get("currentId")
    now = int(time.time())

    user_message = {
        "id": user_msg_id,
        "parentId": prev_id,
        "childrenIds": [assistant_msg_id],
        "role": "user",
        "content": prompt,
        "timestamp": now,
    }
    assistant_message = {
        "id": assistant_msg_id,
        "parentId": user_msg_id,
        "childrenIds": [],
        "role": "assistant",
        "content": "",
        "model": model_id,
        "timestamp": now,
    }

    if prev_id and prev_id in messages and isinstance(messages[prev_id], dict):
        prior = messages[prev_id]
        prior_children = list(prior.get("childrenIds") or [])
        if user_msg_id not in prior_children:
            prior_children.append(user_msg_id)
        prior["childrenIds"] = prior_children
        messages[prev_id] = prior

    messages[user_msg_id] = user_message
    messages[assistant_msg_id] = assistant_message
    history["messages"] = messages
    history["currentId"] = assistant_msg_id
    chat_data["history"] = history
    Chats.update_chat_by_id(subagent_chat_id, chat_data)


def _load_inner_api_messages(
    subagent_chat_id: str, up_to_message_id: str, system_prompt: str
) -> list[dict]:
    """Build the API-shaped message list for the inner run.

    System message first (our composed subagent prompt), then the subagent's
    chat history converted via ``blocks_to_api_messages``. The trailing blank
    assistant message is dropped automatically by ``blocks_to_api_messages``
    (it has no content / tool_calls / reasoning to emit)."""
    chat = Chats.get_chat_by_id(subagent_chat_id)
    if not chat:
        raise RuntimeError(f"subagent chat {subagent_chat_id} not found")
    messages_map = ((chat.chat or {}).get("history") or {}).get("messages") or {}
    ordered = get_message_list(messages_map, up_to_message_id) or []
    api_history = blocks_to_api_messages(ordered)
    api_messages: list[dict] = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(api_history)
    return api_messages


def _extract_final_text(subagent_chat_id: str, assistant_msg_id: str) -> str:
    """Read the final assistant text from the subagent chat row.

    Prefers ``blocks_to_plain_text(content_blocks)`` (canonical, clean) over
    the legacy HTML ``content`` projection. Returns empty string if nothing
    is there — caller decides how to surface that."""
    msg = (
        Chats.get_message_by_id_and_message_id(subagent_chat_id, assistant_msg_id)
        or {}
    )
    blocks = msg.get("content_blocks")
    if isinstance(blocks, list) and blocks:
        # Only render the trailing TEXT blocks — anything before the final
        # text block is reasoning/tool_calls/code_interp that we don't want
        # to repeat back into the parent's context. The subagent's job was
        # to synthesize; the parent only needs that synthesis.
        last_text_blocks: list[dict] = []
        for block in reversed(blocks):
            btype = block.get("type") if isinstance(block, dict) else None
            if btype == "text":
                last_text_blocks.insert(0, block)
            elif btype in ("tool_calls", "code_interpreter"):
                break
            elif btype == "reasoning":
                continue
        if last_text_blocks:
            text = blocks_to_plain_text(last_text_blocks).strip()
            if text:
                return text
        # Fallback: full plain text projection (includes reasoning quotes,
        # tool markers). Still better than nothing.
        return blocks_to_plain_text(blocks).strip()
    content = msg.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _reset_inner_history(subagent_chat_id: str) -> None:
    """Wipe the subagent chat's history back to empty. Used between the first
    failed attempt and the auto-retry so we send a clean slate the second
    time (otherwise the broken half of round-1 corrupts round-2)."""
    chat = Chats.get_chat_by_id(subagent_chat_id)
    if not chat:
        return
    chat_data = chat.chat or {}
    chat_data["history"] = {"messages": {}, "currentId": None}
    Chats.update_chat_by_id(subagent_chat_id, chat_data)


# ---------------------------------------------------------------------------
# Inner-chat orchestrator (called by both launch and continue)
# ---------------------------------------------------------------------------


async def _run_inner_chat(
    *,
    request: Request,
    user,
    subagent_model: dict,
    subagent_chat_id: str,
    prompt: str,
    parent_metadata: dict,
    parent_event_emitter: Callable,
    parent_event_call: Optional[Callable],
    subagent_meta: dict,
    chat_params: dict,
) -> str:
    """Drive one inner subagent turn end-to-end. Returns the final assistant
    text. Raises on unrecoverable error (caller decides retry vs. surface).

    ``subagent_meta`` is the small dict the forwarding emitter stamps into
    every outbound ``chat:subagent:update`` event so the parent UI can route
    updates to the right subagent block: ``{subagent_id, num, name,
    parent_message_id, tool_call_id}``.
    """
    subagent_model_id = subagent_model.get("id")
    if not subagent_model_id:
        raise RuntimeError("subagent model has no id")

    # 1. Append the user prompt + blank assistant to the subagent chat history.
    user_msg_id = str(uuid4())
    assistant_msg_id = str(uuid4())
    _append_history_for_inner_run(
        subagent_chat_id=subagent_chat_id,
        prompt=prompt,
        user_msg_id=user_msg_id,
        assistant_msg_id=assistant_msg_id,
        model_id=subagent_model_id,
    )

    # 2. Compose the inner system prompt + load full history as API messages.
    system_prompt = _compose_subagent_system_prompt(request, subagent_model_id)
    api_messages = _load_inner_api_messages(
        subagent_chat_id, assistant_msg_id, system_prompt
    )

    # 3. Build inner_form_data + inner_metadata.
    extra_tool_ids = list(chat_params.get("subagentExtraToolIds") or [])
    inner_tool_ids = list({"builtin:web_search", *extra_tool_ids})
    inner_form_data: dict = {
        "model": subagent_model_id,
        "messages": api_messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "tool_ids": inner_tool_ids,
        "features": {},  # MUST be empty — no nesting, no image_gen, no memory
        "params": {"function_calling": "native"},
    }
    # Optional per-chat output cap (user wanted defaults to be infinite).
    max_out_tokens = chat_params.get("subagentMaxOutputTokens")
    if max_out_tokens:
        try:
            inner_form_data["max_tokens"] = int(max_out_tokens)
        except (TypeError, ValueError):
            pass

    subagent_socket_info = {
        "user_id": user.id,
        "session_id": parent_metadata.get("session_id"),
        "chat_id": subagent_chat_id,
        "message_id": assistant_msg_id,
    }

    forwarding_emitter = _build_forwarding_emitter(
        subagent_socket_info=subagent_socket_info,
        parent_event_emitter=parent_event_emitter,
        subagent_meta=subagent_meta,
    )
    subagent_event_caller = get_event_call(subagent_socket_info)

    inner_metadata: dict = {
        "user_id": user.id,
        "chat_id": subagent_chat_id,
        "message_id": assistant_msg_id,
        "session_id": parent_metadata.get("session_id"),
        "tool_ids": inner_tool_ids,
        "tool_servers": None,
        "files": None,
        "features": {},
        "variables": {},
        "timezone": parent_metadata.get("timezone"),
        "model": subagent_model,
        "direct": False,
        "params": {"function_calling": "native"},
        # Override hooks — process_chat_response in middleware respects these
        # in place of the default get_event_emitter(metadata) lookup.
        "event_emitter_override": forwarding_emitter,
        "event_caller_override": subagent_event_caller,
        # Flag so any downstream code can detect "this run is inside a
        # subagent" and avoid nesting / re-triggering features.
        "subagent_inner": True,
    }
    # Optional per-chat iteration cap.
    max_iter = chat_params.get("subagentMaxIterations")
    if max_iter:
        try:
            inner_metadata["max_tool_call_retries"] = int(max_iter)
        except (TypeError, ValueError):
            pass

    inner_form_data["metadata"] = inner_metadata

    # 4. Swap request.state for the inner run. Restore on exit.
    saved_state = {
        "metadata": getattr(request.state, "metadata", None),
        "model": getattr(request.state, "model", None),
        "direct": getattr(request.state, "direct", False),
    }
    try:
        request.state.metadata = inner_metadata
        request.state.model = subagent_model
        request.state.direct = False

        # 5. Re-enter the full chat pipeline for the inner run.
        form_data, metadata, events = await process_chat_payload(
            request, inner_form_data, user, inner_metadata, subagent_model
        )
        response = await chat_completion_handler(request, form_data, user)
        await process_chat_response(
            request,
            response,
            form_data,
            user,
            metadata,
            subagent_model,
            events,
            tasks=None,  # no title/tag/follow-up generation for subagents
        )
    finally:
        # Restore parent's request.state so the rest of the parent's pipeline
        # sees what it expected.
        for k, v in saved_state.items():
            if v is None and not hasattr(request.state, k):
                continue
            setattr(request.state, k, v)
        # Clean up MCP clients spun up by inner process_chat_payload (mirrors
        # the same cleanup in main.py's process_chat finally block).
        try:
            inner_mcp_clients = inner_metadata.get("mcp_clients")
            if inner_mcp_clients:
                for client in inner_mcp_clients.values():
                    await client.disconnect()
        except Exception as e:  # noqa: BLE001
            log.debug(f"subagent mcp cleanup: {e}")

    # 6. Read the final text out of the subagent chat row.
    return _extract_final_text(subagent_chat_id, assistant_msg_id)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


async def run_subagent_launch(
    *,
    request: Optional[Request],
    user_dict: Optional[dict],
    parent_metadata: Optional[dict],
    parent_event_emitter: Optional[Callable],
    parent_event_call: Optional[Callable],
    parent_model: Optional[dict],
    name: str,
    prompt: str,
    background: str = "",
) -> str:
    """Spawn and run a fresh subagent. Returns the formatted tool-result string
    the parent model will see.

    Auto-retries once on unexpected errors (per the agreed design). Returns a
    user-visible error string on retry exhaustion. Propagates
    ``asyncio.CancelledError`` so parent cancellation tears down cleanly.
    """
    if request is None or user_dict is None or parent_metadata is None or parent_event_emitter is None:
        return "Subagent ERROR: tool was invoked without required runtime context"

    user = Users.get_user_by_id(user_dict.get("id"))
    if user is None:
        return "Subagent ERROR: user context unavailable"

    parent_chat_id = parent_metadata.get("chat_id")
    parent_message_id = parent_metadata.get("message_id")
    if not parent_chat_id or not parent_message_id:
        return "Subagent ERROR: parent chat context unavailable"

    parent_chat = Chats.get_chat_by_id_and_user_id(parent_chat_id, user.id)
    if parent_chat is None:
        return "Subagent ERROR: parent chat not accessible"

    # Disambiguate name + assign num.
    all_runs = _gather_all_subagent_runs(parent_chat)
    final_name, was_renamed = _disambiguate_name((name or "").strip(), all_runs)
    num = len(all_runs) + 1

    # Resolve subagent model.
    subagent_model_id = _resolve_subagent_model_id(request, parent_chat, parent_model)
    if subagent_model_id is None:
        return f"Subagent {num} ({final_name}) ERROR: no model configured/available"
    subagent_model = request.app.state.MODELS[subagent_model_id]

    # Atomic create with subagent_of meta — never appears in main chat list.
    subagent_chat_title = f"{final_name} (subagent of {parent_chat.title})"
    subagent_chat = Chats.import_chat(
        user.id,
        ChatImportForm(
            **{
                "chat": {
                    "title": subagent_chat_title,
                    "models": [subagent_model_id],
                    "history": {"messages": {}, "currentId": None},
                    "messages": [],
                    "params": {},
                },
                "meta": {
                    "subagent_of": parent_chat_id,
                    "subagent_id": None,  # filled in below now that we know the row id
                    "subagent_name": final_name,
                    "subagent_num": num,
                },
            }
        ),
    )
    if subagent_chat is None:
        return f"Subagent {num} ({final_name}) ERROR: could not create subagent chat row"
    subagent_id = subagent_chat.id
    # Patch meta.subagent_id so the side fields all reference the row's id.
    try:
        Chats.update_chat_by_id(
            subagent_id,
            {
                **(subagent_chat.chat or {}),
                "meta": {
                    "subagent_of": parent_chat_id,
                    "subagent_id": subagent_id,
                    "subagent_name": final_name,
                    "subagent_num": num,
                },
            },
        )
    except Exception as e:  # noqa: BLE001
        log.debug(f"subagent meta patch failed (non-fatal): {e}")

    # Read the parent tool_call_id from middleware's per-task ContextVar
    # (set in `_execute_tool_call` right before invoking us). The contextvar
    # is the right primitive here: when the parent's tool loop runs
    # parallelizable tools via asyncio.gather, each branch has its own value.
    tool_call_id = current_tool_call_id_var.get() or ""
    # Stamp side channel so middleware can attach subagent_id to the tool
    # call result entry (powers `<details type="subagent_launch" id="...">`
    # in serialize_content_blocks).
    if not hasattr(request.state, "subagent_id_by_tool_call"):
        request.state.subagent_id_by_tool_call = {}
    if tool_call_id:
        request.state.subagent_id_by_tool_call[tool_call_id] = subagent_id

    subagent_meta = {
        "subagent_id": subagent_id,
        "num": num,
        "name": final_name,
        "parent_message_id": parent_message_id,
        "tool_call_id": tool_call_id,
        "chat_id": subagent_id,
    }
    started_at = int(time.time())
    _upsert_subagent_run(
        parent_chat_id,
        parent_message_id,
        subagent_id,
        {
            "subagent_id": subagent_id,
            "num": num,
            "name": final_name,
            "chat_id": subagent_id,
            "tool_call_id": tool_call_id,
            "status": "running",
            "prompt": prompt,
            "background": background,
            "started_at": started_at,
        },
    )
    try:
        await parent_event_emitter(
            {
                "type": "chat:subagent:start",
                "data": subagent_meta,
            }
        )
    except Exception as e:  # noqa: BLE001
        log.debug(f"chat:subagent:start emit failed: {e}")

    # Compose the inner-run prompt: prompt + optional background block.
    inner_prompt = prompt or ""
    if background:
        inner_prompt = (
            f"{inner_prompt}\n\n<background>\n{background}\n</background>"
        ).strip()

    chat_params = ((parent_chat.chat or {}).get("params")) or {}

    # Auto-retry once on unexpected errors. Cancellations propagate (don't
    # retry on user-stop).
    last_error: Optional[str] = None
    for attempt in (1, 2):
        try:
            final_text = await _run_inner_chat(
                request=request,
                user=user,
                subagent_model=subagent_model,
                subagent_chat_id=subagent_id,
                prompt=inner_prompt,
                parent_metadata=parent_metadata,
                parent_event_emitter=parent_event_emitter,
                parent_event_call=parent_event_call,
                subagent_meta=subagent_meta,
                chat_params=chat_params,
            )
            if not final_text:
                # Treat empty final text as an error so the retry loop catches
                # it. (Empty tool result back to the parent is a bad UX —
                # tells the parent model nothing.)
                raise RuntimeError("subagent produced no final text")
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                subagent_id,
                {
                    "status": "done",
                    "ended_at": int(time.time()),
                    "final_text": final_text,
                },
            )
            prefix = f"Subagent {num} ({final_name}) output:\n\n"
            if was_renamed:
                # Surface rename so the parent model uses the right name in
                # subagent_continue later.
                prefix = (
                    f"Note: the name you chose was already taken in this "
                    f"chat; this subagent was registered as '{final_name}'.\n\n"
                    + prefix
                )
            return f"{prefix}{final_text}"
        except asyncio.CancelledError:
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                subagent_id,
                {
                    "status": "cancelled",
                    "ended_at": int(time.time()),
                },
            )
            raise
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            log.exception(
                f"subagent {final_name} attempt {attempt}/2 failed: {e}"
            )
            if attempt == 1:
                # Wipe the subagent history so the retry is a clean run.
                _reset_inner_history(subagent_id)
                continue
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                subagent_id,
                {
                    "status": "error",
                    "ended_at": int(time.time()),
                    "error": {"message": last_error},
                },
            )
            return (
                f"Subagent {num} ({final_name}) ERROR after retry: "
                f"{last_error or 'unknown error'}"
            )
    # Defensive — loop always returns. This line shouldn't be reachable.
    return f"Subagent {num} ({final_name}) ERROR: unreachable code path"


async def run_subagent_continue(
    *,
    request: Optional[Request],
    user_dict: Optional[dict],
    parent_metadata: Optional[dict],
    parent_event_emitter: Optional[Callable],
    parent_event_call: Optional[Callable],
    parent_model: Optional[dict],
    name_or_id: str,
    prompt: str,
) -> str:
    """Continue a previously-launched subagent with one more turn."""
    if request is None or user_dict is None or parent_metadata is None or parent_event_emitter is None:
        return "Subagent ERROR: tool was invoked without required runtime context"

    user = Users.get_user_by_id(user_dict.get("id"))
    if user is None:
        return "Subagent ERROR: user context unavailable"

    parent_chat_id = parent_metadata.get("chat_id")
    parent_message_id = parent_metadata.get("message_id")
    if not parent_chat_id or not parent_message_id:
        return "Subagent ERROR: parent chat context unavailable"

    parent_chat = Chats.get_chat_by_id_and_user_id(parent_chat_id, user.id)
    if parent_chat is None:
        return "Subagent ERROR: parent chat not accessible"

    # Resolve name_or_id against existing subagent_runs.
    all_runs = _gather_all_subagent_runs(parent_chat)
    if not all_runs:
        return f"Subagent ERROR: no subagent named or numbered '{name_or_id}' exists in this chat"

    target_id: Optional[str] = None
    needle = (name_or_id or "").strip()
    # First try exact id match.
    if needle in all_runs:
        target_id = needle
    else:
        # Then name match — most recently started wins, case-insensitive.
        candidates = [
            (sid, run)
            for sid, run in all_runs.items()
            if isinstance(run, dict)
            and (run.get("name") or "").lower() == needle.lower()
        ]
        if candidates:
            candidates.sort(
                key=lambda kv: int((kv[1] or {}).get("started_at") or 0),
                reverse=True,
            )
            target_id = candidates[0][0]
        else:
            # Last shot: numeric num match.
            try:
                target_num = int(needle)
                for sid, run in all_runs.items():
                    if isinstance(run, dict) and (run.get("num") == target_num):
                        target_id = sid
                        break
            except (TypeError, ValueError):
                pass

    if target_id is None:
        return f"Subagent ERROR: no subagent named '{name_or_id}' found in this chat"

    target_run = all_runs[target_id]
    target_name = target_run.get("name") or "subagent"
    target_num = target_run.get("num") or 0

    # Load the subagent chat row.
    subagent_chat = Chats.get_chat_by_id_and_user_id(target_id, user.id)
    if subagent_chat is None:
        return f"Subagent {target_num} ({target_name}) ERROR: subagent chat row missing"

    # Resolve subagent model — prefer what the original subagent was using;
    # fall back to per-chat / global / parent.
    subagent_model_id = None
    sa_models = (subagent_chat.chat or {}).get("models") or []
    if sa_models and sa_models[0] in request.app.state.MODELS:
        subagent_model_id = sa_models[0]
    else:
        subagent_model_id = _resolve_subagent_model_id(
            request, parent_chat, parent_model
        )
    if subagent_model_id is None:
        return (
            f"Subagent {target_num} ({target_name}) ERROR: no model available "
            f"to continue this subagent"
        )
    subagent_model = request.app.state.MODELS[subagent_model_id]

    # Side-channel + chat:subagent:start (new tool_call_id, same subagent_id).
    tool_call_id = current_tool_call_id_var.get() or ""
    if not hasattr(request.state, "subagent_id_by_tool_call"):
        request.state.subagent_id_by_tool_call = {}
    if tool_call_id:
        request.state.subagent_id_by_tool_call[tool_call_id] = target_id

    subagent_meta = {
        "subagent_id": target_id,
        "num": target_num,
        "name": target_name,
        "parent_message_id": parent_message_id,
        "tool_call_id": tool_call_id,
        "chat_id": target_id,
        "continuation": True,
    }
    started_at = int(time.time())
    # Continuations get their OWN entry under subagent_runs (keyed by
    # tool_call_id when we have one, else falling back to subagent_id with a
    # round suffix). This lets each tool call's collapsible block stay
    # independent in the parent UI.
    continue_entry_key = (
        f"{target_id}#{tool_call_id}" if tool_call_id else f"{target_id}#{started_at}"
    )
    _upsert_subagent_run(
        parent_chat_id,
        parent_message_id,
        continue_entry_key,
        {
            "subagent_id": target_id,
            "num": target_num,
            "name": target_name,
            "chat_id": target_id,
            "tool_call_id": tool_call_id,
            "continuation": True,
            "status": "running",
            "prompt": prompt,
            "started_at": started_at,
        },
    )
    subagent_meta["entry_key"] = continue_entry_key
    try:
        await parent_event_emitter(
            {
                "type": "chat:subagent:start",
                "data": subagent_meta,
            }
        )
    except Exception as e:  # noqa: BLE001
        log.debug(f"chat:subagent:start (continue) emit failed: {e}")

    chat_params = ((parent_chat.chat or {}).get("params")) or {}

    last_error: Optional[str] = None
    for attempt in (1, 2):
        try:
            final_text = await _run_inner_chat(
                request=request,
                user=user,
                subagent_model=subagent_model,
                subagent_chat_id=target_id,
                prompt=prompt or "",
                parent_metadata=parent_metadata,
                parent_event_emitter=parent_event_emitter,
                parent_event_call=parent_event_call,
                subagent_meta=subagent_meta,
                chat_params=chat_params,
            )
            if not final_text:
                raise RuntimeError("subagent produced no final text")
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                continue_entry_key,
                {
                    "status": "done",
                    "ended_at": int(time.time()),
                    "final_text": final_text,
                },
            )
            return (
                f"Subagent {target_num} ({target_name}) continued — output:\n\n"
                f"{final_text}"
            )
        except asyncio.CancelledError:
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                continue_entry_key,
                {"status": "cancelled", "ended_at": int(time.time())},
            )
            raise
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            log.exception(
                f"subagent {target_name} continue attempt {attempt}/2 failed: {e}"
            )
            if attempt == 1:
                # For continues, DO NOT wipe history — that'd destroy the
                # prior research. Just retry against the existing state. The
                # retry's user message is already appended (it's the same
                # message_id from attempt 1) so we have to undo + redo.
                # Simpler: just retry as-is; the second attempt will append
                # YET another user message + blank assistant, doubling the
                # turns. That's ugly but doesn't lose data. Accept for v1.
                continue
            _upsert_subagent_run(
                parent_chat_id,
                parent_message_id,
                continue_entry_key,
                {
                    "status": "error",
                    "ended_at": int(time.time()),
                    "error": {"message": last_error},
                },
            )
            return (
                f"Subagent {target_num} ({target_name}) continue ERROR after retry: "
                f"{last_error or 'unknown error'}"
            )
    return f"Subagent {target_num} ({target_name}) continue ERROR: unreachable"
