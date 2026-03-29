"""Realtime sideband protocol runtime."""


import asyncio
import json
import logging
import time
from typing import Optional
from uuid import uuid4

from open_webui.models.chats import Chats
from open_webui.realtime.chat_sync import (
    build_assistant_output_message_item,
    cleanup_realtime_voice_turns,
    emit_turn_output,
    ensure_chat_created,
    ensure_realtime_voice_turn,
    ensure_trailing_assistant_output_message,
    maybe_gc_turn,
    persist_turn_output,
    remove_orphan_turn_messages,
    resolve_realtime_voice_assistant_reply_message,
)
from open_webui.realtime.events import emit_status, emit_to_user
from open_webui.realtime.pending_store import drain_pending_texts
from open_webui.realtime.chat_sync import create_realtime_text_turn, create_voice_turn_messages
from open_webui.realtime.constants import ASSISTANT_LISTENING_PLACEHOLDER
from open_webui.realtime.session_state import (
    RealtimeSession,
    cancel_all_timers,
    cancel_checkin_timer,
    end_session,
    maybe_emit_ready,
    record_user_activity,
    reset_bootstrap_flags,
    restart_all_timers,
    restart_checkin_timer_only,
)
from open_webui.realtime.turn_state import VoiceTurn

log = logging.getLogger(__name__)


class _SidebandClosed(Exception):
    def __init__(self, code: int):
        super().__init__(f"Sideband closed with code {code}")
        self.code = code


async def _flush_pending_to_ws(
    session: RealtimeSession, messages: list[dict], context: str, sio=None
) -> bool:
    """Send pending text messages to the OpenAI sideband WebSocket.

    For each message, extracts ``_turn_meta`` (if present) to create a
    ``VoiceTurn`` for turn tracking using the **frontend-generated** message
    IDs, persists the message pair to the DB, and emits ``chat:message:create``
    so the frontend knows about the turn.  Strips ``_turn_meta`` before
    sending to OpenAI.  Sends a trailing ``response.create`` to trigger
    the model's reply.

    Returns True if any messages were sent.
    """
    if not messages or not session.ws:
        return False

    for message in messages:
        turn_meta = message.pop("_turn_meta", None)
        if turn_meta and session.turn_state:
            # Use the frontend's IDs so frontend and backend agree.
            user_msg_id = turn_meta.get("parent_message_id") or str(uuid4())
            asst_msg_id = turn_meta.get("message_id") or str(uuid4())
            parent_id = turn_meta.get("parent_id", "")
            text_content = turn_meta.get("text_content", "")
            item_id = turn_meta.get("item_id", message.get("item", {}).get("id", ""))

            create_realtime_text_turn(
                session,
                item_id=item_id,
                user_message_id=user_msg_id,
                assistant_message_id=asst_msg_id,
                parent_message_id=parent_id,
                user_text=text_content,
            )

            # Persist message pair to DB and notify frontend.
            try:
                await create_voice_turn_messages(
                    chat_id=session.chat_id,
                    parent_id=parent_id,
                    user_msg_id=user_msg_id,
                    asst_msg_id=asst_msg_id,
                    model_id=session.model_id,
                    user_content=text_content,
                )
                if sio:
                    await emit_to_user(
                        sio,
                        session.user_id,
                        session.chat_id,
                        asst_msg_id,
                        {
                            "type": "chat:message:create",
                            "data": {
                                "chatId": session.chat_id,
                                "parentId": parent_id,
                                "userMessage": {
                                    "id": user_msg_id,
                                    "role": "user",
                                    "content": text_content,
                                },
                                "assistantMessage": {
                                    "id": asst_msg_id,
                                    "role": "assistant",
                                    "content": "",
                                    "model": session.model_id,
                                },
                                "currentId": asst_msg_id,
                            },
                        },
                    )
            except Exception:
                log.exception("Failed to persist/emit pending text turn")

        event_id = str(uuid4())
        message["event_id"] = event_id
        session.track_event_id(event_id, f"{context}_flush")
        await session.ws.send(json.dumps(message))

    response_event_id = str(uuid4())
    session.track_event_id(response_event_id, f"{context}_response_create")
    await session.ws.send(
        json.dumps({"type": "response.create", "event_id": response_event_id})
    )
    return True


async def _maybe_apply_provider_idle_timeout(session: RealtimeSession) -> None:
    if not session.ws or session.config.vad_type != "server_vad":
        return
    if not session.config.idle_timeout_ms:
        return

    try:
        idle_timeout_ms = int(session.config.idle_timeout_ms)
    except (TypeError, ValueError):
        return

    session_update = {
        "audio": {
            "input": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": session.config.server_vad_threshold,
                    "silence_duration_ms": session.config.server_vad_silence_duration_ms,
                    "prefix_padding_ms": session.config.server_vad_prefix_padding_ms,
                    "create_response": session.config.vad_create_response,
                    "interrupt_response": session.config.vad_interrupt_response,
                    "idle_timeout_ms": idle_timeout_ms,
                }
            }
        },
    }
    await session.send_event(
        "session.update",
        {"session": session_update},
        context="provider_idle_timeout_update",
    )


async def _execute_tool_calls(
    session: RealtimeSession, function_calls: list[dict], sio, turn: Optional[VoiceTurn] = None
) -> None:
    from open_webui.realtime.tool_runtime import execute_realtime_tool_call

    if not turn:
        turn = session.turn_state.get_active_turn()
    message_id = turn.assistant_message_id if turn else ""

    event_emitter = None
    if session.event_emitter_factory and message_id:
        event_emitter = session.event_emitter_factory(
            {
                "user_id": session.user_id,
                "chat_id": session.chat_id,
                "message_id": message_id,
            }
        )

    event_caller = None
    if session.event_caller_factory and message_id:
        event_caller = session.event_caller_factory(
            {
                "session_id": session.session_id,
                "chat_id": session.chat_id,
                "message_id": message_id,
            }
        )

    metadata = {
        "chat_id": session.chat_id,
        "message_id": message_id,
        "session_id": session.session_id,
    }

    pending_tool_cards: list[tuple[dict, dict]] = []

    if turn and turn.assistant_transcript and not turn.assistant_output:
        turn.assistant_output.append(
            build_assistant_output_message_item(
                text=turn.assistant_transcript, status="completed"
            )
        )

    for function_call in function_calls:
        fn_name = function_call.get("name", "")
        fn_call_id = function_call.get("call_id", "") or function_call.get("id", "")

        tool_card = {
            "type": "function_call",
            "id": fn_call_id,
            "call_id": fn_call_id,
            "name": fn_name,
            "arguments": function_call.get("arguments", "{}"),
            "status": "in_progress",
        }
        pending_tool_cards.append((function_call, tool_card))
        if turn:
            turn.assistant_output.append(tool_card)

    if turn and pending_tool_cards:
        await emit_turn_output(session, turn, sio)

    for function_call, tool_card in pending_tool_cards:
        fn_name = function_call.get("name", "")
        fn_call_id = function_call.get("call_id", "") or function_call.get("id", "")
        if event_emitter:
            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "description": f"Calling {fn_name}...",
                        "done": False,
                        "activity": "tool",
                        "callId": session.call_id,
                    },
                }
            )

        result = await execute_realtime_tool_call(
            tool_call_id=fn_call_id,
            tool_function_name=fn_name,
            tool_args=function_call.get("arguments", "{}"),
            tools=session.tools_dict,
            request=session.tool_request,
            user=session.user,
            metadata=metadata,
            event_emitter=event_emitter,
            event_caller=event_caller,
        )

        if event_emitter:
            for source in result.get("sources", []):
                await event_emitter({"type": "source", "data": source})

        tool_card["status"] = "failed" if result.get("failed") else "completed"
        tool_card["arguments"] = function_call.get("arguments", "{}")

        if turn:
            result_item = {
                "type": "function_call_output",
                "id": f"fco_{uuid4().hex}",
                "call_id": fn_call_id,
                "output": [{"type": "input_text", "text": result.get("content", "")}],
                "status": "failed" if result.get("failed") else "completed",
            }
            if result.get("files"):
                result_item["files"] = result.get("files")
            if result.get("embeds"):
                result_item["embeds"] = result.get("embeds")
            turn.assistant_output.append(result_item)

        if event_emitter:
            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "description": (
                            f"{fn_name} failed"
                            if result.get("failed")
                            else f"{fn_name} completed"
                        ),
                        "done": True,
                        "activity": "tool",
                        "callId": session.call_id,
                    },
                }
            )

        await session.send_event(
            "conversation.item.create",
            {
                "item": {
                    "type": "function_call_output",
                    "call_id": fn_call_id,
                    "output": result.get("content", ""),
                }
            },
            context=f"tool_result:{fn_name}",
        )

    if turn and turn.assistant_output:
        ensure_trailing_assistant_output_message(turn)
        await emit_turn_output(session, turn, sio)
        await persist_turn_output(session, turn)

    await session.send_event("response.create", context="tool_response_create")


async def _handle_sideband_event(
    session: RealtimeSession,
    event_type: str,
    data: dict,
    sio,
) -> None:
    """Route a single sideband event through the session's state machine."""
    session.touch_activity()

    if event_type == "session.created":
        session.session_created = True
        await maybe_emit_ready(session, sio)

    elif event_type == "session.updated":
        session.session_update_ack = True
        await maybe_emit_ready(session, sio)

    elif event_type == "input_audio_buffer.speech_started":
        await record_user_activity(session, sio)

        item_id = data.get("item_id", "")
        turn = await ensure_realtime_voice_turn(session, sio, item_id=item_id)
        if not turn:
            return

    elif event_type == "input_audio_buffer.speech_stopped":
        await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Processing...", False)
        await restart_all_timers(session, sio)

    elif event_type == "input_audio_buffer.committed":
        await record_user_activity(session, sio)
        item_id = data.get("item_id", "")
        turn = await ensure_realtime_voice_turn(session, sio, item_id=item_id)
        if not turn:
            return

    elif event_type == "conversation.item.input_audio_transcription.delta":
        delta = data.get("delta", "")
        item_id = data.get("item_id", "")
        turn = session.turn_state.get_turn_by_input_item(item_id)
        if turn:
            session.turn_state.append_user_transcript(turn.turn_id, delta)
            await emit_to_user(
                sio,
                session.user_id,
                session.chat_id,
                turn.user_message_id,
                {
                    "type": "chat:message:delta",
                    "data": {"id": turn.user_message_id, "content": delta},
                },
            )

    elif event_type == "conversation.item.input_audio_transcription.completed":
        transcript = data.get("transcript", "")
        item_id = data.get("item_id", "")
        turn = session.turn_state.get_turn_by_input_item(item_id)
        if turn:
            session.turn_state.finalize_user_transcript(turn.turn_id, transcript)

            if turn.is_empty:
                await remove_orphan_turn_messages(
                    session.chat_id,
                    turn.user_message_id,
                    turn.assistant_message_id,
                    turn.parent_message_id,
                )
                await emit_to_user(
                    sio,
                    session.user_id,
                    session.chat_id,
                    turn.user_message_id,
                    {"type": "chat:message:prune"},
                )
                session.turn_state.gc_turn(turn.turn_id)
                return

            await emit_to_user(
                sio,
                session.user_id,
                session.chat_id,
                turn.user_message_id,
                {
                    "type": "replace",
                    "data": {"id": turn.user_message_id, "content": transcript},
                },
            )

            await asyncio.to_thread(
                Chats.upsert_message_to_chat_by_id_and_message_id,
                session.chat_id,
                turn.user_message_id,
                {
                    "id": turn.user_message_id,
                    "role": "user",
                    "content": transcript,
                    "timestamp": int(time.time()),
                },
                advance_current=False,
            )

            if turn.is_assistant_done:
                output_message = ensure_trailing_assistant_output_message(
                    turn, status="completed"
                )
                output_message["content"][-1]["text"] = turn.assistant_transcript
                await emit_turn_output(session, turn, sio, done=True)

            maybe_gc_turn(session, turn)

    elif event_type == "response.created":
        response = data.get("response", {})
        response_id = response.get("id", "")
        session.assistant_responding = True

        if session.pending_transient_response_kind == "idle_checkin" and response_id:
            session.transient_response_ids.add(response_id)
            session.pending_transient_response_kind = None
        else:
            turn = session.turn_state.get_pending_assistant_turn()
            if turn and response_id:
                session.turn_state.bind_response(response_id, turn.turn_id)

        if session.await_bootstrap_replay_response:
            session.await_bootstrap_replay_response = False
            await maybe_emit_ready(session, sio)

    elif event_type == "response.output_audio_transcript.delta":
        delta = data.get("delta", "")
        response_id = data.get("response_id", "")
        if response_id in session.transient_response_ids:
            return
        turn = session.turn_state.get_turn_by_response(response_id)
        if turn:
            session.turn_state.append_assistant_transcript(turn.turn_id, delta)
            output_message = ensure_trailing_assistant_output_message(turn)
            output_message["content"][-1]["text"] = turn.assistant_transcript
            await emit_turn_output(session, turn, sio)

    elif event_type == "response.output_audio_transcript.done":
        transcript = data.get("transcript", "")
        response_id = data.get("response_id", "")
        if response_id in session.transient_response_ids:
            return
        turn = session.turn_state.get_turn_by_response(response_id)
        if turn:
            session.turn_state.finalize_assistant_transcript(turn.turn_id, transcript)
            output_message = ensure_trailing_assistant_output_message(
                turn, status="completed"
            )
            output_message["content"][-1]["text"] = turn.assistant_transcript
            await emit_turn_output(session, turn, sio, done=turn.is_user_done)

    elif event_type == "output_audio_buffer.started":
        response_id = data.get("response_id", "")
        if response_id in session.transient_response_ids:
            log.debug("TIMER:PING:CANCEL (checkin audio started playing)")
            await cancel_checkin_timer(session)
        else:
            log.debug("TIMER:SESSION:CANCEL + TIMER:PING:CANCEL (model audio started playing)")
            await cancel_all_timers(session)

    elif event_type == "output_audio_buffer.stopped":
        response_id = data.get("response_id", "")
        is_checkin = response_id in session.transient_response_ids
        if is_checkin:
            session.transient_response_ids.discard(response_id)
            await restart_checkin_timer_only(session, sio)
        else:
            await restart_all_timers(session, sio)

    elif event_type == "response.done":
        response = data.get("response", {})
        response_id = response.get("id", "")
        is_transient_response = response_id in session.transient_response_ids
        session.assistant_responding = False

        if is_transient_response:
            await emit_status(sio, session.user_id, session.chat_id, session.call_id, "", True)
            return

        turn = session.turn_state.get_turn_by_response(response_id)

        if session.pending_settings_updates and session.ws:
            merged = {}
            for update in session.pending_settings_updates:
                setting = update.get("setting", "")
                value = update.get("value")
                if setting and value is not None:
                    merged[setting] = value
            session.pending_settings_updates.clear()

            if merged:
                recreate_settings = {}
                for key in ("voice",):
                    if key in merged:
                        recreate_settings[key] = merged.pop(key)

                if merged:
                    session_update: dict = {}
                    for key, val in merged.items():
                        if key == "speed":
                            session_update.setdefault("audio", {}).setdefault("output", {})[
                                "speed"
                            ] = float(val)
                        elif key in ("max_output_tokens", "max_tokens"):
                            session_update["max_output_tokens"] = (
                                int(val)
                                if str(val).strip().lower() not in {"inf", "-1", ""}
                                else "inf"
                            )
                        elif key == "noise_reduction":
                            session_update.setdefault("audio", {}).setdefault("input", {})[
                                "noise_reduction"
                            ] = ({"type": val} if val else None)
                        elif key == "vad_type":
                            turn_detection = None
                            if val == "semantic_vad":
                                turn_detection = {"type": "semantic_vad"}
                            elif val == "server_vad":
                                turn_detection = {"type": "server_vad"}
                            session_update.setdefault("audio", {}).setdefault("input", {})[
                                "turn_detection"
                            ] = turn_detection

                    event_id = str(uuid4())
                    session.track_event_id(event_id, f"settings_flush:{','.join(merged.keys())}")
                    session_update.setdefault("type", "realtime")
                    await session.ws.send(
                        json.dumps(
                            {
                                "type": "session.update",
                                "event_id": event_id,
                                "session": session_update,
                            }
                        )
                    )
                if recreate_settings:
                    for key, value in recreate_settings.items():
                        await session.apply_setting(key, value, sio=sio)

        function_calls = [
            item
            for item in response.get("output", [])
            if item.get("type") == "function_call"
        ]
        if function_calls and session.tools_dict:
            session.tool_executing = True
            try:
                await _execute_tool_calls(session, function_calls, sio, turn=turn)
            except Exception as exc:
                log.exception(
                    "Tool execution failed for session %s", session.session_id
                )
                await session.send_event("response.create", context="tool_error_recovery")
            finally:
                session.tool_executing = False
            return

        if turn:
            turn.is_assistant_done = True

            output_message = ensure_trailing_assistant_output_message(
                turn, status="completed"
            )
            output_message["content"][-1]["text"] = turn.assistant_transcript

            await emit_turn_output(session, turn, sio, done=True)
            await persist_turn_output(session, turn)

            maybe_gc_turn(session, turn)

        await emit_status(sio, session.user_id, session.chat_id, session.call_id, "", True)

        # After the model finishes responding, drain any pending texts
        # that arrived via the cross-worker Redis store while the model
        # was generating its response.
        active_pending = await drain_pending_texts(session.session_id)
        await _flush_pending_to_ws(session, active_pending, "active_pending", sio=sio)

    elif event_type == "error":
        error = data.get("error", {})
        error_msg = error.get("message", str(error))
        event_id = data.get("event_id", "")

        context = session.lookup_event_id(event_id) if event_id else None
        if context == "provider_idle_timeout_update":
            log.warning(
                "Provider idle timeout update rejected for %s: %s",
                session.session_id, error_msg,
            )
            session.config.idle_timeout_ms = ""
            return
        if context:
            log.error(
                "Sideband error for %s (action=%s, event_id=%s): %s",
                session.session_id, context, event_id, error_msg,
            )
        else:
            log.error("Sideband error for %s: %s", session.session_id, error_msg)

        await emit_to_user(
            sio,
            session.user_id,
            session.chat_id,
            "",
            {"type": "chat:message:error", "data": {"error": {"content": error_msg}}},
        )

        error_type = error.get("type", "")
        if error_type in (
            "rate_limit_exceeded",
            "server_error",
            "invalid_request_error",
        ):
            log.warning(
                "Fatal error '%s' — ending session %s", error_type, session.session_id
            )
            await end_session(
                session,
                sio,
                "sideband_error",
                message=error_msg,
            )


async def start_sideband(
    session: RealtimeSession,
    api_key: str,
    base_url: str,
    sio,
) -> None:
    """Connect the sideband WebSocket and start the event loop."""
    # Reset all bootstrap flags so stale state from a failed prior
    # attempt does not cause premature ready or skipped flushes.
    reset_bootstrap_flags(session)

    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{ws_base}/realtime?call_id={session.call_id}"

    import websockets

    try:
        session.ws = await websockets.connect(
            url,
            additional_headers={"Authorization": f"Bearer {api_key}"},
        )
        session.sideband_connected = True
        await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Preparing voice session...", False)

        replay_unanswered_user_turn = None
        if session.config.context_enabled:
            from open_webui.realtime.context_builder import (
                build_bootstrap_context,
                build_conversation_items,
                build_summary_conversation_item,
                generate_context_summary,
            )

            unanswered_last_user_turn = (
                session.config.context_unanswered_last_user_turn
                if not session.pending_messages
                else "discard"
            )
            await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Loading conversation history...", False)
            bootstrap = await build_bootstrap_context(
                session.chat_id,
                recent_exchanges_limit=session.config.context_recent_exchanges_limit,
                older_summary_exchanges_limit=session.config.context_max_history_exchanges,
                older_summary_bytes_limit=session.config.context_max_history_bytes,
                unanswered_last_user_turn=unanswered_last_user_turn,
            )

            system_summary = None
            if session.config.context_summarize and bootstrap.summary_messages:
                await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Summarizing conversation context...", False)
                system_summary = await generate_context_summary(
                    bootstrap.summary_messages,
                    summary_prompt=session.config.context_summary_prompt,
                    summary_max_size=session.config.context_summary_max_size,
                    request=session.tool_request,
                    user=session.user,
                )

            items = []
            summary_item = build_summary_conversation_item(system_summary)
            if summary_item:
                items.append(summary_item)

            items.extend(build_conversation_items(bootstrap.replay_messages))

            replay_unanswered_user_turn = bootstrap.unresolved_user_turn
            if replay_unanswered_user_turn:
                items.extend(build_conversation_items([replay_unanswered_user_turn]))

            if items:
                await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Injecting context...", False)
            for item in items:
                event_id = str(uuid4())
                item_copy = {**item, "event_id": event_id}
                session.track_event_id(event_id, "context_injection")
                await session.ws.send(json.dumps(item_copy))

        if replay_unanswered_user_turn and replay_unanswered_user_turn.get("id"):
            assistant_message_id = await resolve_realtime_voice_assistant_reply_message(
                session.chat_id,
                replay_unanswered_user_turn["id"],
                session.model_id,
                assistant_content=ASSISTANT_LISTENING_PLACEHOLDER,
            )
            if assistant_message_id:
                turn_id = str(uuid4())
                session.turn_state.create_turn(
                    turn_id=turn_id,
                    user_message_id=replay_unanswered_user_turn["id"],
                    assistant_message_id=assistant_message_id,
                    parent_message_id=replay_unanswered_user_turn.get("parentId") or "",
                )
                session.turn_state.finalize_user_transcript(
                    turn_id,
                    replay_unanswered_user_turn.get("content", ""),
                )
                await emit_to_user(
                    sio,
                    session.user_id,
                    session.chat_id,
                    assistant_message_id,
                    {
                        "type": "chat:message:create",
                        "data": {
                            "chatId": session.chat_id,
                            "parentId": replay_unanswered_user_turn["id"],
                            "assistantMessage": {
                                "id": assistant_message_id,
                                "role": "assistant",
                                "content": ASSISTANT_LISTENING_PLACEHOLDER,
                                "model": session.model_id,
                            },
                            "currentId": assistant_message_id,
                        },
                    },
                )
            else:
                log.warning(
                    "Unable to create assistant reply placeholder for replayed turn "
                    "session=%s chat=%s",
                    session.session_id, session.chat_id,
                )
                replay_unanswered_user_turn = None

        session.context_injected = True
        await emit_status(sio, session.user_id, session.chat_id, session.call_id, "", True)
        if replay_unanswered_user_turn:
            session.ready_auto_unmute = False
            session.await_bootstrap_replay_response = True
            replay_event_id = str(uuid4())
            session.track_event_id(replay_event_id, "bootstrap_replay_response_create")
            await session.ws.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "event_id": replay_event_id,
                    }
                )
            )
        await maybe_emit_ready(session, sio)

        # Drain pending texts from BOTH the local session list AND the
        # cross-worker Redis store.  This covers single-worker (local list)
        # and multi-worker (Redis store) modes.
        all_pending = list(session.pending_messages)
        all_pending.extend(await drain_pending_texts(session.session_id))
        if await _flush_pending_to_ws(session, all_pending, "pending", sio=sio):
            session.pending_messages.clear()  # only clear after successful flush

        session.pending_messages_flushed = True
        await maybe_emit_ready(session, sio)
        await _maybe_apply_provider_idle_timeout(session)

        # Re-drain once more after emitting ready — catches messages that
        # arrived between the first drain and the state transition.
        late_pending = await drain_pending_texts(session.session_id)
        await _flush_pending_to_ws(session, late_pending, "late_pending", sio=sio)

        session.state = "active"

        async for message in session.ws:
            try:
                event_data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                continue

            event_type = event_data.get("type", "")
            await _handle_sideband_event(session, event_type, event_data, sio)

        raise _SidebandClosed(getattr(session.ws, "close_code", 1000) or 1000)
    except asyncio.CancelledError:
        pass
    finally:
        # Always clear bootstrap status so the mic is never stuck locked.
        try:
            await emit_status(sio, session.user_id, session.chat_id, session.call_id, "", True)
        except Exception:
            pass
        if session.ws:
            try:
                await session.ws.close()
            except Exception:
                pass
        session.ws = None
        session.sideband_connected = False


def _extract_error_code(exc: Exception) -> int:
    """Extract HTTP or WS close code from a websockets exception."""
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", 0)
    status_code = getattr(exc, "status_code", 0)
    if status_code:
        return status_code
    rcvd = getattr(exc, "rcvd", None)
    if rcvd is not None:
        return getattr(rcvd, "code", 0)
    return getattr(exc, "code", 0)


async def start_sideband_with_retry(
    session: RealtimeSession,
    api_key: str,
    base_url: str,
    sio,
    max_retries: int = 2,
) -> None:
    """Start the sideband with exponential backoff reconnection."""
    for attempt in range(max_retries):
        if session.state in ("ending", "idle"):
            return

        try:
            await start_sideband(session, api_key, base_url, sio)
            return
        except asyncio.CancelledError:
            return
        except Exception as exc:
            code = _extract_error_code(exc)

            if code in (401, 403):
                log.error(
                    "Sideband auth failed (%d) for session %s — not retrying",
                    code, session.session_id,
                )
                await end_session(session, sio, "auth_error", message=str(exc))
                return

            if code == 404:
                log.error(
                    "Sideband call_id invalid (404) for session %s — not retrying",
                    session.session_id,
                )
                await end_session(session, sio, "sideband_error", message=str(exc))
                return

            if code in (1000, 1001):
                await end_session(session, sio, "sideband_closed")
                return

            if attempt == 0:
                await sio.emit(
                    "realtime:sideband_lost",
                    {
                        "callId": session.call_id,
                        "attempt": 1,
                        "max_retries": max_retries,
                    },
                    room=session.session_id,
                )

            if code == 429:
                log.warning(
                    "Sideband rate-limited (429) for session %s", session.session_id
                )
            else:
                log.warning(
                    "Sideband attempt %d/%d failed for session %s (code=%d): %s",
                    attempt + 1, max_retries, session.session_id, code, exc,
                )

            if session.state not in ("ending", "idle"):
                session.state = "connecting"

        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    log.error("All %d sideband retries failed for session %s", max_retries, session.session_id)
    await end_session(
        session,
        sio,
        "sideband_error",
        message="Open WebUI: Realtime sideband connection failed after retries.",
    )
