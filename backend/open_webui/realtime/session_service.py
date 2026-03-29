"""Realtime session service façade and orchestration entrypoints."""


import asyncio
import logging
import time
from typing import Optional
from uuid import uuid4

from open_webui.models.chats import Chats
from open_webui.realtime.ownership import claim_start
from open_webui.realtime.bootstrap import (
    SUPPORTED_REALTIME_SETTINGS,
    SessionConfig,
    apply_user_realtime_settings,
    build_ephemeral_key_body,
    build_session_config,
    convert_tools_to_realtime_format,
    mint_realtime_client_secret,
)
from open_webui.realtime.catalog import get_effective_provider_model_id
from open_webui.realtime.chat_sync import (
    build_realtime_content_items,
    create_realtime_text_turn,
    create_voice_turn_messages,
    ensure_typed_realtime_assistant_message,
    extract_visible_text_from_content,
    get_realtime_typed_turn_metadata,
    run_session_end_background_tasks,
    cleanup_realtime_voice_turns,
)
from open_webui.realtime.events import emit_to_user
from open_webui.realtime.contracts import (
    build_realtime_bootstrap_binding,
    realtime_event_payload,
)
from open_webui.realtime.ephemeral_store import pop_ephemeral_key
from open_webui.realtime.session_state import (
    RealtimeSession,
    SessionManager,
    can_reuse_session,
    end_session,
    prepare_session_bootstrap,
    record_user_activity,
    session_manager,
)
from open_webui.realtime.sideband import start_sideband_with_retry
from open_webui.realtime.tool_runtime import RealtimeToolAuthContext, resolve_realtime_tools

log = logging.getLogger(__name__)

session_manager.cleanup_turns = cleanup_realtime_voice_turns
session_manager.session_end_background_tasks = run_session_end_background_tasks


async def _prepare_realtime_session_runtime(
    *,
    sid,
    user,
    model_id: str,
    chat_id: str,
    call_id: str,
    app_config,
    event_emitter_factory=None,
    event_caller_factory=None,
    app=None,
    tool_ids=None,
    tool_servers=None,
    features=None,
    terminal_id=None,
    key_data: Optional[dict] = None,
) -> tuple[Optional[RealtimeSession], Optional[SessionConfig]]:
    config = build_session_config(app_config) if app_config else None
    if not config:
        return None, None

    model_obj = app.state.MODELS.get(model_id, {}) if app else {}
    provider_model_id = get_effective_provider_model_id(model_obj) or model_id
    config.model = provider_model_id

    event_emitter = None
    if event_emitter_factory:
        event_emitter = event_emitter_factory(
            {"user_id": user["id"], "chat_id": chat_id, "message_id": ""},
            update_db=False,
        )

    existing_session = session_manager.get_session(sid)
    if can_reuse_session(
        existing_session,
        chat_id=chat_id,
        model_id=model_id,
        user_id=user["id"],
    ):
        session = existing_session
        if not session.config:
            session.config = config
    else:
        session = await session_manager.create_session(
            session_id=sid,
            chat_id=chat_id,
            model_id=model_id,
            user_id=user["id"],
            event_emitter=event_emitter,
        )
        session.config = config

    session.model_id = model_id
    session.chat_id = chat_id
    session.user_id = user["id"]
    session.config.model = provider_model_id
    config = session.config
    session.call_id = call_id
    session.ephemeral_key = None
    session.event_emitter = event_emitter
    session.event_emitter_factory = event_emitter_factory
    session.event_caller_factory = event_caller_factory
    session.app = app
    session.tools_dict = {}
    prepare_session_bootstrap(session)

    # Claim ownership — sets voice_session_id and generation
    voice_session_id = session.voice_session_id or str(uuid4())
    ownership_record = await claim_start(
        voice_session_id=voice_session_id,
        user_id=user["id"],
        sid=sid,
        call_id=call_id or "",
        model_id=model_id,
        chat_id=chat_id,
    )
    if ownership_record:
        session.voice_session_id = ownership_record.voice_session_id
        session.generation = ownership_record.generation
    else:
        session.voice_session_id = voice_session_id
        session.generation = 1
        log.warning("claim_start returned None for voice_session_id=%s", voice_session_id)

    user_model = None
    if app:
        from open_webui.models.users import Users

        user_model = await asyncio.to_thread(Users.get_user_by_id, user["id"])
        session.user = user_model
        apply_user_realtime_settings(config, user_model)

    eph_key = key_data.get("value") if key_data else None

    stored_tool_ids = key_data.get("tool_ids", []) if key_data else (tool_ids or [])
    stored_tool_servers = key_data.get("tool_servers", []) if key_data else (tool_servers or [])
    stored_features = key_data.get("features", {}) if key_data else (features or {})
    stored_terminal_id = key_data.get("terminal_id") if key_data else terminal_id

    if app and user_model:
        try:
            tool_request, resolved_tools = await resolve_realtime_tools(
                app=app,
                user=user_model,
                model=model_obj,
                chat_id=chat_id,
                session_id=sid,
                tool_ids=stored_tool_ids,
                tool_servers=stored_tool_servers,
                terminal_id=stored_terminal_id,
                features=stored_features,
                auth_context=RealtimeToolAuthContext(
                    session_token=(key_data or {}).get("session_token", ""),
                    oauth_session_id=(key_data or {}).get(
                        "oauth_session_id", ""
                    ),
                ),
                event_emitter=event_emitter,
            )
            session.tool_request = tool_request
            if resolved_tools:
                session.tools_dict = resolved_tools
        except Exception as exc:
            log.exception("Tool resolution failed for session %s", sid)

    session.ephemeral_key = eph_key
    return session, config


async def start_realtime_session(
    sid,
    user,
    model_id,
    chat_id,
    call_id,
    sio,
    app_config,
    event_emitter_factory=None,
    event_caller_factory=None,
    app=None,
    tool_ids=None,
    tool_servers=None,
    features=None,
    terminal_id=None,
):
    key_data = await pop_ephemeral_key(call_id) if call_id else None
    if call_id and not key_data:
        log.warning("No bootstrap state found for call_id=%s", call_id)
        await sio.emit(
            "realtime:ended",
            realtime_event_payload(
                call_id=call_id,
                reason="sideband_error",
                message="Open WebUI: Missing realtime bootstrap state for this call.",
            ),
            room=sid,
        )
        return None

    if key_data:
        expected = build_realtime_bootstrap_binding(
            user_id=key_data.get("user_id", ""),
            sid=key_data.get("sid", ""),
            chat_id=key_data.get("chat_id", ""),
            model_id=key_data.get("model_id", ""),
            tool_ids=key_data.get("tool_ids", []),
            tool_servers=key_data.get("tool_servers", []),
            features=key_data.get("features", {}),
            terminal_id=key_data.get("terminal_id"),
        )
        actual = build_realtime_bootstrap_binding(
            user_id=user["id"],
            sid=sid,
            chat_id=chat_id,
            model_id=model_id,
            tool_ids=tool_ids or [],
            tool_servers=tool_servers or [],
            features=features or {},
            terminal_id=terminal_id,
        )
        for field_name, expected_value in expected.items():
            actual_value = actual.get(field_name)
            # Allow chat_id mismatch when negotiate was called before the chat existed
            # (empty or local: placeholder at negotiate time, real ID at start time)
            if field_name == "chat_id" and (
                not expected_value or str(expected_value).startswith("local:")
            ):
                continue
            if actual_value != expected_value:
                log.warning(
                    "realtime:start rejected: bootstrap binding mismatch "
                    "sid=%s field=%s",
                    sid, field_name,
                )
                await sio.emit(
                    "realtime:ended",
                    realtime_event_payload(
                        call_id=call_id,
                        reason="forbidden",
                        message="Open WebUI: Realtime bootstrap binding check failed.",
                    ),
                    room=sid,
                )
                return None

    session, config = await _prepare_realtime_session_runtime(
        sid=sid,
        user=user,
        model_id=model_id,
        chat_id=chat_id,
        call_id=call_id,
        app_config=app_config,
        event_emitter_factory=event_emitter_factory,
        event_caller_factory=event_caller_factory,
        app=app,
        tool_ids=tool_ids,
        tool_servers=tool_servers,
        features=features,
        terminal_id=terminal_id,
        key_data=key_data,
    )
    if not session or not config:
        await sio.emit(
            "realtime:ended",
            realtime_event_payload(
                call_id=call_id,
                reason="config_error",
                message="Open WebUI: Realtime configuration is incomplete.",
            ),
            room=sid,
        )
        return None

    from open_webui.utils.access_control import get_permissions

    user_permissions = get_permissions(
        user["id"], getattr(app_config, "USER_PERMISSIONS", {})
    )
    rt_perms = user_permissions.get("realtime", {}).get("settings", {})
    allowed_settings = [
        key for key, value in rt_perms.items() if value and key in SUPPORTED_REALTIME_SETTINGS
    ]
    await sio.emit(
        "realtime:session",
        realtime_event_payload(
            call_id=call_id,
            voice_session_id=session.voice_session_id,
            generation=session.generation,
            sessionConfig={
                "model": model_id,
                "voice": config.voice,
                "vadType": config.vad_type,
                "speed": config.speed,
                "noiseReduction": config.noise_reduction,
                "maxOutputTokens": config.max_response_output_tokens,
                "contextEnabled": config.context_enabled,
            },
            allowedSettings=allowed_settings,
        ),
        room=sid,
    )

    if call_id and session.ephemeral_key:
        base_url = str(getattr(app_config, "AUDIO_RT_API_BASE_URL", ""))
        if base_url:
            session.ws_task = asyncio.create_task(
                start_sideband_with_retry(session, session.ephemeral_key, base_url, sio)
            )
        else:
            log.error("Missing base_url — sideband cannot start")
            await end_session(
                session,
                sio,
                "sideband_error",
                message="Open WebUI: Realtime API base URL is not configured.",
            )
    else:
        log.error("No ephemeral key found for call_id=%s — sideband cannot start", call_id)
        if call_id:
            await end_session(
                session,
                sio,
                "sideband_error",
                message="Open WebUI: Missing realtime session credentials.",
            )

    return session


async def orphan_sweep_loop(sio, app_config) -> None:
    """Background task that runs every 60s to clean up orphaned sessions."""
    while True:
        try:
            await asyncio.sleep(60)
            session_timeout = int(getattr(app_config, "AUDIO_RT_SESSION_TIMEOUT", 300))
            if session_timeout > 0:
                now = time.time()
                for session in session_manager.all_sessions():
                    if session.state not in ("active", "connecting", "reconnecting"):
                        continue
                    elapsed = now - session.last_activity
                    if elapsed > session_timeout:
                        log.warning(
                            "Orphan sweep: tearing down idle session %s "
                            "(idle %.0fs > %ds)",
                            session.session_id, elapsed, session_timeout,
                        )
                        await session_manager.teardown_session(
                            session.session_id,
                            reason="idle",
                            sio=sio,
                        )
                        await sio.emit(
                            "realtime:ended",
                            realtime_event_payload(
                                call_id=session.call_id,
                                voice_session_id=session.voice_session_id,
                                generation=session.generation,
                                reason="idle",
                            ),
                            room=session.session_id,
                        )
            # Clean up stale ownership records for ended sessions
            try:
                from open_webui.realtime.ownership import cleanup_ended_records
                cleanup_ended_records()
            except Exception:
                log.debug("Ownership cleanup skipped", exc_info=True)

        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Error in orphan sweep loop")


async def _prepare_typed_realtime_turn(
    session: RealtimeSession,
    content,
    request,
    sio,
    *,
    create_fallback_pair: bool,
    item_id: Optional[str] = None,
) -> dict:
    content_items = build_realtime_content_items(content)
    if not item_id:
        item_id = uuid4().hex
    text_content = extract_visible_text_from_content(content)
    parent_message, assistant_message_id = await get_realtime_typed_turn_metadata(
        request, session.chat_id
    )

    if parent_message.get("id"):
        assistant_message_id = await ensure_typed_realtime_assistant_message(
            session, parent_message, assistant_message_id, sio
        )
        if assistant_message_id:
            create_realtime_text_turn(
                session,
                item_id,
                parent_message["id"],
                assistant_message_id,
                parent_message.get("parentId") or "",
                text_content,
            )
    elif create_fallback_pair:
        user_message_id = str(uuid4())
        assistant_message_id = str(uuid4())

        parent_id = ""
        existing_chat = await asyncio.to_thread(Chats.get_chat_by_id, session.chat_id)
        if existing_chat and existing_chat.chat:
            parent_id = existing_chat.chat.get("history", {}).get("currentId", "")

        create_realtime_text_turn(
            session,
            item_id,
            user_message_id,
            assistant_message_id,
            parent_id,
            text_content,
        )
        await create_voice_turn_messages(
            chat_id=session.chat_id,
            parent_id=parent_id,
            user_msg_id=user_message_id,
            asst_msg_id=assistant_message_id,
            model_id=session.model_id,
            user_content=text_content,
        )

        if sio:
            await emit_to_user(
                sio,
                session.user_id,
                session.chat_id,
                assistant_message_id,
                {
                    "type": "chat:message:create",
                    "data": {
                        "chatId": session.chat_id,
                        "parentId": parent_id,
                        "userMessage": {
                            "id": user_message_id,
                            "role": "user",
                            "content": text_content,
                        },
                        "assistantMessage": {
                            "id": assistant_message_id,
                            "role": "assistant",
                            "content": "",
                            "model": session.model_id,
                        },
                        "currentId": assistant_message_id,
                    },
                },
            )

    return {
        "type": "conversation.item.create",
        "item": {
            "id": item_id,
            "type": "message",
            "role": "user",
            "content": content_items,
        },
    }
