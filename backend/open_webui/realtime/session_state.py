"""Realtime session state and lifecycle helpers."""


import asyncio
import json
import logging
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from open_webui.config import AUDIO_RT_DEFAULT_IDLE_CALL_CHECKIN_PROMPT
from open_webui.realtime.contracts import realtime_event_payload
from open_webui.realtime.events import emit_status
from open_webui.realtime.turn_state import TurnStateManager

log = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Configuration snapshot frozen at session start."""

    model: str = ""
    voice: str = "marin"
    vad_type: str = "server_vad"
    server_vad_threshold: float = 0.5
    server_vad_silence_duration_ms: int = 500
    server_vad_prefix_padding_ms: int = 300
    semantic_vad_eagerness: str = "auto"
    transcription_model: str = "gpt-4o-transcribe"
    transcription_language: str = ""
    transcription_prompt: str = ""
    noise_reduction: str = "near_field"
    system_instructions: str = ""
    max_response_output_tokens: str = ""
    speed: float = 1.0
    idle_timeout_ms: str = ""
    session_timeout_seconds: int = 180
    idle_call_checkin_interval_seconds: int = 45
    idle_call_checkin_prompt: str = AUDIO_RT_DEFAULT_IDLE_CALL_CHECKIN_PROMPT
    vad_create_response: bool = True
    vad_interrupt_response: bool = True
    context_enabled: bool = False
    context_recent_exchanges_limit: int = 10
    context_max_history_exchanges: int = 40
    context_max_history_bytes: int = 16000
    context_summarize: bool = False
    context_unanswered_last_user_turn: str = "discard"
    context_summary_prompt: str = ""
    context_summary_max_size: int = 2000
    tool_specs: list[dict] = field(default_factory=list)
    truncation_strategy: str = "auto"
    truncation_retention_ratio: float = 0.8
    truncation_token_limit: str = ""


@dataclass
class RealtimeSession:
    """State for a single realtime session."""

    session_id: str
    chat_id: str
    model_id: str
    user_id: str
    call_id: Optional[str] = None
    ephemeral_key: Optional[str] = None
    voice_session_id: str = ""
    generation: int = 0

    state: str = "idle"
    config: SessionConfig = field(default_factory=SessionConfig)
    turn_state: TurnStateManager = field(default_factory=TurnStateManager)

    ws: Optional[Any] = None  # websockets.ClientConnection at runtime
    ws_task: Optional[asyncio.Task] = None
    event_emitter: Optional[Callable[..., Any]] = None
    event_emitter_factory: Optional[Callable[..., Any]] = None
    event_caller_factory: Optional[Callable[..., Any]] = None

    session_created: bool = False
    sideband_connected: bool = False
    session_update_ack: bool = False
    context_injected: bool = False
    pending_messages_flushed: bool = False
    ready_emitted: bool = False
    pending_messages: list[dict] = field(default_factory=list)
    ready_auto_unmute: bool = True
    await_bootstrap_replay_response: bool = False

    event_id_cache: OrderedDict = field(default_factory=OrderedDict)
    EVENT_ID_CACHE_MAX: int = 100
    last_activity: float = field(default_factory=time.time)

    pending_settings_updates: list[dict] = field(default_factory=list)
    tools_dict: dict = field(default_factory=dict)
    tool_request: Optional[Any] = None
    app: Optional[Any] = None
    user: Optional[Any] = None
    assistant_responding: bool = False
    tool_executing: bool = False
    last_user_activity: float = field(default_factory=time.monotonic)
    user_idle_timeout_task: Optional[asyncio.Task] = None
    idle_checkin_task: Optional[asyncio.Task] = None
    pending_transient_response_kind: Optional[str] = None
    transient_response_ids: set[str] = field(default_factory=set)
    _chat_creation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def is_ready(self) -> bool:
        # Initial call readiness is based on bootstrap completion; later
        # session.update acknowledgements are tracked separately.
        return (
            self.sideband_connected
            and self.context_injected
            and self.pending_messages_flushed
        )

    def track_event_id(self, event_id: str, context: str) -> None:
        self.event_id_cache[event_id] = context
        if len(self.event_id_cache) > self.EVENT_ID_CACHE_MAX:
            self.event_id_cache.popitem(last=False)

    def lookup_event_id(self, event_id: str) -> Optional[str]:
        return self.event_id_cache.get(event_id)

    def touch_activity(self) -> None:
        self.last_activity = time.time()

    async def send_event(
        self, event_type: str, payload: Optional[dict] = None, context: Optional[str] = None
    ) -> None:
        if not self.ws:
            return
        event = {"type": event_type}
        if payload:
            event.update(payload)
        # GA API requires session.type for every session.update
        if event_type == "session.update" and isinstance(event.get("session"), dict):
            event["session"].setdefault("type", "realtime")
        event_id = str(uuid4())
        event["event_id"] = event_id
        self.track_event_id(event_id, context or event_type)
        try:
            await self.ws.send(json.dumps(event))
        except Exception as exc:
            log.warning(
                "Failed to send sideband event '%s' for %s: %s",
                event_type, self.session_id, exc,
            )
            return

    async def apply_setting(self, setting: str, value, sio=None) -> None:
        # Settings that require session recreation (new ephemeral key)
        if setting == "voice":
            self.config.voice = value
            await self._teardown_sideband()
            self.session_created = False
            self.session_update_ack = False
            self.context_injected = False
            self.pending_messages_flushed = False
            self.ready_emitted = False
            self.state = "reconnecting"
            if sio:
                await sio.emit(
                    "realtime:ended",
                    realtime_event_payload(
                        call_id=self.call_id,
                        voice_session_id=self.voice_session_id,
                        generation=self.generation,
                        reason="voice_change",
                    ),
                    room=self.session_id,
                )
            return

        # Settings that can be applied via session.update
        session_update: dict = {}
        if setting == "speed":
            speed = float(value)
            if not math.isfinite(speed):
                log.warning("Rejected non-finite speed value: %s", value)
                return
            session_update.setdefault("audio", {}).setdefault("output", {})["speed"] = speed
        elif setting == "max_tokens":
            if str(value).strip().lower() in {"inf", "-1", ""}:
                session_update["max_output_tokens"] = "inf"
            else:
                tokens = int(value)
                if tokens < 1 or tokens > 65536:
                    log.warning("Rejected out-of-range max_tokens: %s", value)
                    return
                session_update["max_output_tokens"] = tokens
        elif setting == "noise_reduction":
            session_update.setdefault("audio", {}).setdefault("input", {})[
                "noise_reduction"
            ] = ({"type": value} if value else None)
        elif setting == "vad_type":
            turn_detection = None
            if value == "semantic_vad":
                turn_detection = {
                    "type": "semantic_vad",
                    "eagerness": self.config.semantic_vad_eagerness,
                    "create_response": self.config.vad_create_response,
                    "interrupt_response": self.config.vad_interrupt_response,
                }
            elif value == "server_vad":
                turn_detection = {
                    "type": "server_vad",
                    "threshold": self.config.server_vad_threshold,
                    "silence_duration_ms": self.config.server_vad_silence_duration_ms,
                    "prefix_padding_ms": self.config.server_vad_prefix_padding_ms,
                    "create_response": self.config.vad_create_response,
                    "interrupt_response": self.config.vad_interrupt_response,
                }
            self.config.vad_type = value
            session_update.setdefault("audio", {}).setdefault("input", {})[
                "turn_detection"
            ] = turn_detection
        elif setting == "context":
            self.config.context_enabled = bool(value)
            return
        else:
            return

        await self.send_event(
            "session.update", {"session": session_update}, f"setting:{setting}"
        )

    async def _teardown_sideband(self) -> None:
        current_task = asyncio.current_task()
        if (
            self.ws_task
            and not self.ws_task.done()
            and self.ws_task is not current_task
        ):
            self.ws_task.cancel()
            try:
                await self.ws_task
            except (asyncio.CancelledError, Exception):
                pass
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        self.ws = None
        self.ephemeral_key = None


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, RealtimeSession] = {}
        self._init_locks: dict[str, asyncio.Lock] = {}
        self.cleanup_turns: Optional[Callable[..., Awaitable[None]]] = None
        self.session_end_background_tasks: Optional[
            Callable[[RealtimeSession], Awaitable[None]]
        ] = None

    def get_session(self, session_id: str) -> Optional[RealtimeSession]:
        return self._sessions.get(session_id)

    def get_session_by_chat(self, chat_id: str) -> Optional[RealtimeSession]:
        for session in self._sessions.values():
            if session.chat_id == chat_id and session.state in (
                "connecting",
                "reconnecting",
                "active",
            ):
                return session
        return None

    async def create_session(
        self,
        session_id: str,
        chat_id: str,
        model_id: str,
        user_id: str,
        event_emitter: Optional[Callable[..., Any]] = None,
    ) -> RealtimeSession:
        existing = self._sessions.get(session_id)
        # Preserve pending_messages from text-first sessions being replaced
        inherited_pending: list[dict] = []
        if existing and existing.state not in ("idle", "ending"):
            # Preserve pending messages — chat_id may differ for new chats
            # (text-first path uses local: or empty, realtime:start uses real ID)
            if existing.pending_messages:
                inherited_pending = list(existing.pending_messages)
                log.debug(
                    "Preserving %d pending_messages from replaced session sid=%s",
                    len(inherited_pending), session_id,
                )
            await self.teardown_session(session_id, reason="replaced")

        existing_chat_session = self.get_session_by_chat(chat_id)
        if existing_chat_session and existing_chat_session.session_id != session_id:
            await self.teardown_session(
                existing_chat_session.session_id, reason="replaced"
            )

        session = RealtimeSession(
            session_id=session_id,
            chat_id=chat_id,
            model_id=model_id,
            user_id=user_id,
            state="connecting",
            event_emitter=event_emitter,
        )
        if inherited_pending:
            session.pending_messages.extend(inherited_pending)
        self._sessions[session_id] = session
        return session

    async def teardown_session(
        self, session_id: str, reason: str = "user", sio=None
    ) -> Optional[RealtimeSession]:
        session = self._sessions.pop(session_id, None)
        if not session:
            return None

        session.state = "ending"
        _cancel_task(session.user_idle_timeout_task)
        _cancel_task(session.idle_checkin_task)
        session.user_idle_timeout_task = None
        session.idle_checkin_task = None

        if reason != "replaced" and self.cleanup_turns:
            await self.cleanup_turns(session, sio=sio, reason=reason)

        await session._teardown_sideband()
        session.turn_state.clear()
        session.state = "idle"

        # Clean up cross-worker pending text store
        from open_webui.realtime.pending_store import cleanup_pending_texts
        await cleanup_pending_texts(session.session_id)

        # Release ownership
        if session.voice_session_id:
            from open_webui.realtime.ownership import release as release_ownership
            await release_ownership(session.voice_session_id)

        if reason not in ("replaced",) and self.session_end_background_tasks:
            task = asyncio.create_task(self.session_end_background_tasks(session))
            task.add_done_callback(
                lambda t: log.error("Session-end background task failed: %s", t.exception())
                if not t.cancelled() and t.exception()
                else None
            )

        return session

    def get_init_lock(self, chat_id: str) -> asyncio.Lock:
        if chat_id not in self._init_locks:
            self._init_locks[chat_id] = asyncio.Lock()
        return self._init_locks[chat_id]

    def all_sessions(self) -> list[RealtimeSession]:
        return list(self._sessions.values())


session_manager = SessionManager()


def can_reuse_session(
    session: Optional[RealtimeSession],
    *,
    chat_id: str,
    model_id: str,
    user_id: str,
) -> bool:
    return bool(
        session
        and session.chat_id == chat_id
        and session.model_id == model_id
        and session.user_id == user_id
        and session.state in ("connecting", "reconnecting")
        and session.ws is None
    )


def reset_bootstrap_flags(session: RealtimeSession) -> None:
    """Reset all bootstrap-related flags to their initial state.

    Called before each sideband connection attempt so that stale flags
    from a failed prior attempt do not cause incorrect ``is_ready``
    evaluation or premature ``realtime:ready`` emission.

    Does NOT touch ``pending_messages`` — those may have been drained
    into a local list by the caller and would be lost if cleared here.
    """
    session.session_created = False
    session.sideband_connected = False
    session.session_update_ack = False
    session.context_injected = False
    session.pending_messages_flushed = False
    session.ready_emitted = False
    session.ready_auto_unmute = True
    session.await_bootstrap_replay_response = False
    session.assistant_responding = False
    session.pending_transient_response_kind = None
    session.transient_response_ids.clear()
    session.event_id_cache.clear()
    session.turn_state.clear()
    if session.user_idle_timeout_task and not session.user_idle_timeout_task.done():
        session.user_idle_timeout_task.cancel()
    if session.idle_checkin_task and not session.idle_checkin_task.done():
        session.idle_checkin_task.cancel()
    session.user_idle_timeout_task = None
    session.idle_checkin_task = None


def prepare_session_bootstrap(session: RealtimeSession) -> None:
    """Full bootstrap preparation including pending_messages flag."""
    reset_bootstrap_flags(session)
    session.pending_messages_flushed = not bool(session.pending_messages)
    if session.state != "ending":
        session.state = "connecting"


async def maybe_emit_ready(session: RealtimeSession, sio) -> None:
    if (
        session.ready_emitted
        or not session.is_ready
        or session.await_bootstrap_replay_response
    ):
        return
    session.ready_emitted = True
    await sio.emit(
        "realtime:ready",
        realtime_event_payload(
            call_id=session.call_id,
            voice_session_id=session.voice_session_id,
            generation=session.generation,
            auto_unmute=session.ready_auto_unmute,
        ),
        room=session.session_id,
    )
    session.last_user_activity = time.monotonic()
    _schedule_user_idle_timeout(session, sio)
    _schedule_idle_checkin(session, sio)


async def end_session(
    session: RealtimeSession, sio, reason: str, message: Optional[str] = None
) -> None:
    if session_manager.get_session(session.session_id) is session:
        await session_manager.teardown_session(
            session.session_id,
            reason=reason,
            sio=sio,
        )
    payload = {"reason": reason}
    if message:
        payload["message"] = message
    await sio.emit(
        "realtime:ended",
        realtime_event_payload(
            call_id=session.call_id,
            voice_session_id=session.voice_session_id,
            generation=session.generation,
            **payload,
        ),
        room=session.session_id,
    )


def _cancel_task(task: Optional[asyncio.Task]) -> None:
    if task and not task.done():
        task.cancel()


async def _user_idle_timeout_loop(
    session: RealtimeSession, sio, timeout_seconds: int
) -> None:
    try:
        await asyncio.sleep(timeout_seconds)
        if session_manager.get_session(session.session_id) is not session:
            log.debug("TIMER:SESSION:TRIGGER:SKIP session gone")
            return
        if session.state in ("ending", "idle"):
            log.debug("TIMER:SESSION:TRIGGER:SKIP state=%s", session.state)
            return
        elapsed = time.monotonic() - session.last_user_activity
        if elapsed < timeout_seconds:
            log.debug("TIMER:SESSION:TRIGGER:SKIP elapsed=%.1fs < %ds", elapsed, timeout_seconds)
            return
        log.info("TIMER:SESSION:TRIGGER elapsed=%.1fs — ending session", elapsed)
        await end_session(session, sio, "idle")
    except asyncio.CancelledError:
        return


async def _idle_checkin_loop(
    session: RealtimeSession, sio, interval_seconds: int
) -> None:
    try:
        await asyncio.sleep(interval_seconds)
        if session_manager.get_session(session.session_id) is not session:
            log.debug("TIMER:PING:TRIGGER:SKIP session gone")
            return
        if session.state not in ("active", "connecting", "reconnecting"):
            log.debug("TIMER:PING:TRIGGER:SKIP state=%s", session.state)
            return
        if not session.ready_emitted or not session.ws:
            log.debug("TIMER:PING:TRIGGER:SKIP not ready or no ws")
            return
        if session.assistant_responding or session.pending_transient_response_kind:
            log.debug("TIMER:PING:TRIGGER:SKIP assistant_responding=%s pending=%s",
                       session.assistant_responding, session.pending_transient_response_kind)
            return

        prompt = (session.config.idle_call_checkin_prompt or "").strip()
        if not prompt:
            log.debug("TIMER:PING:TRIGGER:SKIP no prompt configured")
            return

        log.info("TIMER:PING:TRIGGER firing checkin")
        session.pending_transient_response_kind = "idle_checkin"
        await emit_status(sio, session.user_id, session.chat_id, session.call_id, "Speaking...", False)
        await session.send_event(
            "response.create",
            {
                "response": {
                    "conversation": "none",
                    "instructions": prompt,
                    "input": [],
                    "output_modalities": ["audio"],
                }
            },
            context="idle_checkin_response_create",
        )
    except asyncio.CancelledError:
        return


def _schedule_user_idle_timeout(session: RealtimeSession, sio) -> None:
    timeout_seconds = int(session.config.session_timeout_seconds or 0)
    _cancel_task(session.user_idle_timeout_task)
    session.user_idle_timeout_task = None
    if timeout_seconds <= 0:
        return
    log.debug("TIMER:SESSION:START %ds", timeout_seconds)
    session.user_idle_timeout_task = asyncio.create_task(
        _user_idle_timeout_loop(session, sio, timeout_seconds)
    )


def _schedule_idle_checkin(session: RealtimeSession, sio) -> None:
    interval_seconds = int(session.config.idle_call_checkin_interval_seconds or 0)
    _cancel_task(session.idle_checkin_task)
    session.idle_checkin_task = None
    if interval_seconds <= 0:
        return
    if (
        not session.ready_emitted
        or session.assistant_responding
        or session.pending_transient_response_kind
        or not session.ws
        or session.state not in ("active", "connecting", "reconnecting")
    ):
        log.debug("TIMER:PING:START:SKIP guard blocked (responding=%s pending=%s ready=%s)",
                   session.assistant_responding, session.pending_transient_response_kind,
                   session.ready_emitted)
        return
    log.debug("TIMER:PING:START %ds", interval_seconds)
    session.idle_checkin_task = asyncio.create_task(
        _idle_checkin_loop(session, sio, interval_seconds)
    )


async def cancel_all_timers(session: RealtimeSession) -> None:
    """Cancel both session and checkin timers.  Called when ANY speech
    begins (user or non-checkin model response)."""
    if session.user_idle_timeout_task and not session.user_idle_timeout_task.done():
        log.debug("TIMER:SESSION:CANCEL")
    if session.idle_checkin_task and not session.idle_checkin_task.done():
        log.debug("TIMER:PING:CANCEL")
    _cancel_task(session.user_idle_timeout_task)
    session.user_idle_timeout_task = None
    _cancel_task(session.idle_checkin_task)
    session.idle_checkin_task = None


async def cancel_checkin_timer(session: RealtimeSession) -> None:
    """Cancel only the checkin timer.  Called when checkin speech starts
    (session timer stays running — checkins are invisible to it)."""
    if session.idle_checkin_task and not session.idle_checkin_task.done():
        log.debug("TIMER:PING:CANCEL (checkin speech, session timer untouched)")
    _cancel_task(session.idle_checkin_task)
    session.idle_checkin_task = None


async def restart_all_timers(session: RealtimeSession, sio) -> None:
    """Restart both session and checkin timers.  Called when non-checkin
    speech ends (user stops talking, or model finishes non-checkin audio)."""
    log.debug("TIMER:SESSION:RESTART + TIMER:PING:RESTART")
    session.last_user_activity = time.monotonic()
    session.touch_activity()
    _schedule_user_idle_timeout(session, sio)
    _schedule_idle_checkin(session, sio)


async def restart_checkin_timer_only(session: RealtimeSession, sio) -> None:
    """Restart only the checkin timer.  Called when checkin audio finishes.
    Session timer is untouched (checkins are invisible to it)."""
    log.debug("TIMER:PING:RESTART (session timer untouched)")
    session.touch_activity()
    _schedule_idle_checkin(session, sio)


async def record_user_activity(session: RealtimeSession, sio) -> None:
    """User started speaking.  Cancel both timers immediately.
    Timers restart when speech ends (speech_stopped or output_audio.done)."""
    log.debug("TIMER:SESSION:CANCEL + TIMER:PING:CANCEL (user speaking)")
    session.last_user_activity = time.monotonic()
    session.touch_activity()
    await cancel_all_timers(session)
