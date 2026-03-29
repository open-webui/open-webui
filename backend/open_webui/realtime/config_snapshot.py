"""Shared realtime config snapshot and payload helpers."""


from dataclasses import dataclass, fields
from typing import Any

from open_webui.config import AUDIO_RT_DEFAULT_IDLE_CALL_CHECKIN_PROMPT
from open_webui.realtime.catalog import (
    get_effective_provider_model_id,
    is_realtime_model_id,
)


@dataclass(frozen=True)
class RealtimeConfigSnapshot:
    engine: str = ""
    api_key: str = ""
    api_base_url: str = "https://api.openai.com/v1"
    models: tuple[str, ...] = ()
    voice: str = "marin"
    vad_type: str = "server_vad"
    server_vad_threshold: float = 0.5
    server_vad_silence_duration_ms: int = 500
    server_vad_prefix_padding_ms: int = 300
    semantic_vad_eagerness: str = "auto"
    transcription_model: str = "gpt-4o-transcribe"
    noise_reduction: str = "near_field"
    max_response_output_tokens: str = ""
    context_enabled: bool = False
    context_recent_exchanges_limit: int = 10
    context_max_history_exchanges: int = 40
    context_max_history_bytes: int = 16000
    context_summarize: bool = False
    context_unanswered_last_user_turn: str = "discard"
    context_summary_prompt: str = ""
    context_summary_max_size: int = 2000
    speed: float = 1.0
    transcription_prompt: str = ""
    vad_idle_timeout_ms: str = ""
    vad_create_response: bool = True
    vad_interrupt_response: bool = True
    session_timeout: int = 180
    idle_call_checkin_interval: int = 45
    idle_call_checkin_prompt: str = AUDIO_RT_DEFAULT_IDLE_CALL_CHECKIN_PROMPT
    truncation_strategy: str = "auto"
    truncation_retention_ratio: float = 0.8
    truncation_token_limit: str = ""


REALTIME_CONFIG_MAPPING: tuple[tuple[str, str, str], ...] = (
    ("engine", "ENGINE", "AUDIO_RT_ENGINE"),
    ("api_key", "API_KEY", "AUDIO_RT_API_KEY"),
    ("api_base_url", "API_BASE_URL", "AUDIO_RT_API_BASE_URL"),
    ("models", "MODELS", "AUDIO_RT_MODELS"),
    ("voice", "VOICE", "AUDIO_RT_VOICE"),
    ("vad_type", "VAD_TYPE", "AUDIO_RT_VAD_TYPE"),
    ("server_vad_threshold", "SERVER_VAD_THRESHOLD", "AUDIO_RT_SERVER_VAD_THRESHOLD"),
    (
        "server_vad_silence_duration_ms",
        "SERVER_VAD_SILENCE_DURATION_MS",
        "AUDIO_RT_SERVER_VAD_SILENCE_DURATION_MS",
    ),
    (
        "server_vad_prefix_padding_ms",
        "SERVER_VAD_PREFIX_PADDING_MS",
        "AUDIO_RT_SERVER_VAD_PREFIX_PADDING_MS",
    ),
    (
        "semantic_vad_eagerness",
        "SEMANTIC_VAD_EAGERNESS",
        "AUDIO_RT_SEMANTIC_VAD_EAGERNESS",
    ),
    ("transcription_model", "TRANSCRIPTION_MODEL", "AUDIO_RT_TRANSCRIPTION_MODEL"),
    ("noise_reduction", "NOISE_REDUCTION", "AUDIO_RT_NOISE_REDUCTION"),
    (
        "max_response_output_tokens",
        "MAX_RESPONSE_OUTPUT_TOKENS",
        "AUDIO_RT_MAX_RESPONSE_OUTPUT_TOKENS",
    ),
    ("context_enabled", "CONTEXT_ENABLED", "AUDIO_RT_CONTEXT_ENABLED"),
    (
        "context_recent_exchanges_limit",
        "CONTEXT_RECENT_EXCHANGES_LIMIT",
        "AUDIO_RT_CONTEXT_RECENT_EXCHANGES_LIMIT",
    ),
    (
        "context_max_history_exchanges",
        "CONTEXT_MAX_HISTORY_EXCHANGES",
        "AUDIO_RT_CONTEXT_MAX_HISTORY_EXCHANGES",
    ),
    (
        "context_max_history_bytes",
        "CONTEXT_MAX_HISTORY_BYTES",
        "AUDIO_RT_CONTEXT_MAX_HISTORY_BYTES",
    ),
    ("context_summarize", "CONTEXT_SUMMARIZE", "AUDIO_RT_CONTEXT_SUMMARIZE"),
    (
        "context_unanswered_last_user_turn",
        "CONTEXT_UNANSWERED_LAST_USER_TURN",
        "AUDIO_RT_CONTEXT_UNANSWERED_LAST_USER_TURN",
    ),
    (
        "context_summary_prompt",
        "CONTEXT_SUMMARY_PROMPT",
        "AUDIO_RT_CONTEXT_SUMMARY_PROMPT",
    ),
    (
        "context_summary_max_size",
        "CONTEXT_SUMMARY_MAX_SIZE",
        "AUDIO_RT_CONTEXT_SUMMARY_MAX_SIZE",
    ),
    ("speed", "SPEED", "AUDIO_RT_SPEED"),
    ("transcription_prompt", "TRANSCRIPTION_PROMPT", "AUDIO_RT_TRANSCRIPTION_PROMPT"),
    ("vad_idle_timeout_ms", "VAD_IDLE_TIMEOUT_MS", "AUDIO_RT_VAD_IDLE_TIMEOUT_MS"),
    ("vad_create_response", "VAD_CREATE_RESPONSE", "AUDIO_RT_VAD_CREATE_RESPONSE"),
    (
        "vad_interrupt_response",
        "VAD_INTERRUPT_RESPONSE",
        "AUDIO_RT_VAD_INTERRUPT_RESPONSE",
    ),
    ("session_timeout", "SESSION_TIMEOUT", "AUDIO_RT_SESSION_TIMEOUT"),
    (
        "idle_call_checkin_interval",
        "IDLE_CALL_CHECKIN_INTERVAL",
        "AUDIO_RT_IDLE_CALL_CHECKIN_INTERVAL",
    ),
    (
        "idle_call_checkin_prompt",
        "IDLE_CALL_CHECKIN_PROMPT",
        "AUDIO_RT_IDLE_CALL_CHECKIN_PROMPT",
    ),
    ("truncation_strategy", "TRUNCATION_STRATEGY", "AUDIO_RT_TRUNCATION_STRATEGY"),
    (
        "truncation_retention_ratio",
        "TRUNCATION_RETENTION_RATIO",
        "AUDIO_RT_TRUNCATION_RETENTION_RATIO",
    ),
    ("truncation_token_limit", "TRUNCATION_TOKEN_LIMIT", "AUDIO_RT_TRUNCATION_TOKEN_LIMIT"),
)

_SNAPSHOT_FIELD_DEFAULTS = {field.name: field.default for field in fields(RealtimeConfigSnapshot)}


def read_realtime_config(app_config: Any) -> RealtimeConfigSnapshot:
    values: dict[str, Any] = {}

    for snapshot_attr, _admin_attr, app_config_attr in REALTIME_CONFIG_MAPPING:
        default_value = _SNAPSHOT_FIELD_DEFAULTS[snapshot_attr]
        value = getattr(app_config, app_config_attr, default_value)
        if snapshot_attr == "models":
            value = tuple(value or ())
        values[snapshot_attr] = value

    return RealtimeConfigSnapshot(**values)


def build_realtime_admin_config(
    app_config: Any, *, include_task_model_warning: bool = True
) -> dict[str, Any]:
    snapshot = read_realtime_config(app_config)
    payload = {
        admin_attr: list(getattr(snapshot, snapshot_attr))
        if snapshot_attr == "models"
        else getattr(snapshot, snapshot_attr)
        for snapshot_attr, admin_attr, _app_config_attr in REALTIME_CONFIG_MAPPING
    }
    if include_task_model_warning:
        payload["TASK_MODEL_WARNING"] = get_realtime_task_model_warning(app_config)
    return payload


def apply_realtime_admin_config(app_config: Any, realtime_form: Any) -> None:
    for snapshot_attr, admin_attr, app_config_attr in REALTIME_CONFIG_MAPPING:
        value = getattr(realtime_form, admin_attr)
        if snapshot_attr == "models":
            value = list(value or [])
        setattr(app_config, app_config_attr, value)


def build_realtime_client_defaults(app_config: Any) -> dict[str, Any]:
    snapshot = read_realtime_config(app_config)
    return {
        "voice": snapshot.voice,
        "vad_type": snapshot.vad_type,
        "server_vad_threshold": float(snapshot.server_vad_threshold),
        "server_vad_silence_duration_ms": int(snapshot.server_vad_silence_duration_ms),
        "server_vad_prefix_padding_ms": int(snapshot.server_vad_prefix_padding_ms),
        "semantic_vad_eagerness": str(snapshot.semantic_vad_eagerness),
        "noise_reduction": str(snapshot.noise_reduction),
        "speed": float(snapshot.speed),
        "vad_create_response": bool(snapshot.vad_create_response),
        "vad_interrupt_response": bool(snapshot.vad_interrupt_response),
        "session_timeout": int(snapshot.session_timeout),
        "idle_call_checkin_interval": int(snapshot.idle_call_checkin_interval),
    }


def model_has_realtime_capability(model: Any) -> bool:
    return is_realtime_model_id(get_effective_provider_model_id(model))


def resolve_realtime_model_ids(app_config: Any, models_state: Any = None) -> list[str]:
    snapshot = read_realtime_config(app_config)
    if snapshot.models:
        return list(snapshot.models)

    if not models_state:
        return []

    items = models_state.items() if hasattr(models_state, "items") else []
    seen: set[str] = set()
    realtime_model_ids: list[str] = []

    for _, model in items:
        model_id = get_effective_provider_model_id(model)
        if not is_realtime_model_id(model_id):
            continue

        normalized_model_id = model_id.lower()
        if normalized_model_id in seen:
            continue

        seen.add(normalized_model_id)
        realtime_model_ids.append(model_id)

    return realtime_model_ids


def get_realtime_task_model_warning(app_config: Any) -> bool:
    return getattr(app_config, "AUDIO_RT_ENGINE", "") == "openai" and not getattr(
        app_config, "TASK_MODEL_EXTERNAL", ""
    )
