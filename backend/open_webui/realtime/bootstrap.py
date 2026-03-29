"""Realtime session bootstrap and config translation helpers."""


import logging
from typing import Any, Optional

import aiohttp

from open_webui.realtime.config_snapshot import read_realtime_config
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT
from open_webui.realtime.constants import (
    REALTIME_NOISE_REDUCTION_TYPES,
    REALTIME_SEMANTIC_VAD_EAGERNESS,
    REALTIME_VAD_TYPES,
    get_realtime_voice_ids_for_model,
)
from open_webui.realtime.session_state import SessionConfig

log = logging.getLogger(__name__)


SUPPORTED_REALTIME_SETTINGS = {
    "voice",
    "speed",
    "vad",
    "noise_reduction",
    "max_tokens",
    "context",
}


def build_session_config(app_config: Any) -> SessionConfig:
    """Build a SessionConfig snapshot from the current app config."""
    config = read_realtime_config(app_config)

    return SessionConfig(
        model=str(config.models[0]) if config.models else "",
        voice=str(config.voice),
        vad_type=str(config.vad_type),
        server_vad_threshold=float(config.server_vad_threshold),
        server_vad_silence_duration_ms=int(config.server_vad_silence_duration_ms),
        server_vad_prefix_padding_ms=int(config.server_vad_prefix_padding_ms),
        semantic_vad_eagerness=str(config.semantic_vad_eagerness),
        transcription_model=str(config.transcription_model),
        transcription_language="",
        transcription_prompt=str(config.transcription_prompt),
        noise_reduction=str(config.noise_reduction),
        system_instructions="",
        max_response_output_tokens=str(config.max_response_output_tokens),
        speed=float(config.speed),
        idle_timeout_ms=str(config.vad_idle_timeout_ms),
        session_timeout_seconds=int(config.session_timeout),
        idle_call_checkin_interval_seconds=int(config.idle_call_checkin_interval),
        idle_call_checkin_prompt=str(config.idle_call_checkin_prompt),
        vad_create_response=bool(config.vad_create_response),
        vad_interrupt_response=bool(config.vad_interrupt_response),
        context_enabled=bool(config.context_enabled),
        context_recent_exchanges_limit=int(config.context_recent_exchanges_limit),
        context_max_history_exchanges=int(config.context_max_history_exchanges),
        context_max_history_bytes=int(config.context_max_history_bytes),
        context_summarize=bool(config.context_summarize),
        context_unanswered_last_user_turn=str(config.context_unanswered_last_user_turn),
        context_summary_prompt=str(config.context_summary_prompt),
        context_summary_max_size=int(config.context_summary_max_size),
        truncation_strategy=str(config.truncation_strategy),
        truncation_retention_ratio=float(config.truncation_retention_ratio),
        truncation_token_limit=str(config.truncation_token_limit),
    )


def _get_user_realtime_settings(user_obj: Any) -> dict[str, Any]:
    if not user_obj:
        return {}

    settings_obj = getattr(user_obj, "settings", None)
    if isinstance(settings_obj, dict):
        ui_settings = settings_obj.get("ui", {}) or {}
    else:
        ui_settings = getattr(settings_obj, "ui", {}) or {}

    audio_settings = ui_settings.get("audio", {}) or {}
    realtime_settings = audio_settings.get("realtime", {}) or {}
    return realtime_settings if isinstance(realtime_settings, dict) else {}


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _coerce_float(
    value: Any,
    *,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def _coerce_int(value: Any, *, minimum: Optional[int] = None) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    if minimum is not None and parsed < minimum:
        return None
    return parsed


def apply_user_realtime_settings(config: SessionConfig, user_obj: Any) -> SessionConfig:
    if not config:
        return config

    realtime_settings = _get_user_realtime_settings(user_obj)
    if not realtime_settings:
        return config

    voice = realtime_settings.get("voice")
    supported_voices = get_realtime_voice_ids_for_model(config.model)
    if isinstance(voice, str) and voice in supported_voices:
        config.voice = voice

    speed = _coerce_float(realtime_settings.get("speed"), minimum=0.25, maximum=1.5)
    if speed is not None:
        config.speed = speed

    vad_type = realtime_settings.get("vadType")
    if isinstance(vad_type, str) and vad_type in REALTIME_VAD_TYPES:
        config.vad_type = vad_type

    semantic_vad_eagerness = realtime_settings.get("semanticVadEagerness")
    if (
        isinstance(semantic_vad_eagerness, str)
        and semantic_vad_eagerness in REALTIME_SEMANTIC_VAD_EAGERNESS
    ):
        config.semantic_vad_eagerness = semantic_vad_eagerness

    server_vad_threshold = _coerce_float(
        realtime_settings.get("serverVadThreshold"), minimum=0.0, maximum=1.0
    )
    if server_vad_threshold is not None:
        config.server_vad_threshold = server_vad_threshold

    server_vad_silence_duration_ms = _coerce_int(
        realtime_settings.get("serverVadSilenceDurationMs"), minimum=0
    )
    if server_vad_silence_duration_ms is not None:
        config.server_vad_silence_duration_ms = server_vad_silence_duration_ms

    server_vad_prefix_padding_ms = _coerce_int(
        realtime_settings.get("serverVadPrefixPaddingMs"), minimum=0
    )
    if server_vad_prefix_padding_ms is not None:
        config.server_vad_prefix_padding_ms = server_vad_prefix_padding_ms

    noise_reduction = realtime_settings.get("noiseReduction")
    if (
        isinstance(noise_reduction, str)
        and noise_reduction in REALTIME_NOISE_REDUCTION_TYPES
    ):
        config.noise_reduction = noise_reduction

    vad_create_response = _coerce_bool(realtime_settings.get("vadCreateResponse"))
    if vad_create_response is not None:
        config.vad_create_response = vad_create_response

    vad_interrupt_response = _coerce_bool(
        realtime_settings.get("vadInterruptResponse")
    )
    if vad_interrupt_response is not None:
        config.vad_interrupt_response = vad_interrupt_response

    return config


def convert_tools_to_realtime_format(chat_api_tools: list[dict]) -> list[dict]:
    """Convert Chat Completions tool format to Realtime API format."""
    realtime_tools = []
    for tool in chat_api_tools:
        if tool.get("type") == "function" and "function" in tool:
            function = tool["function"]
            realtime_tools.append(
                {
                    "type": "function",
                    "name": function.get("name", ""),
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {}),
                }
            )
    return realtime_tools


def build_ephemeral_key_body(config: SessionConfig, model: str) -> dict:
    """Build request body for POST /v1/realtime/client_secrets."""
    if config.vad_type == "semantic_vad":
        turn_detection = {
            "type": "semantic_vad",
            "eagerness": config.semantic_vad_eagerness,
            "create_response": config.vad_create_response,
            "interrupt_response": config.vad_interrupt_response,
        }
    elif config.vad_type == "server_vad":
        turn_detection = {
            "type": "server_vad",
            "threshold": config.server_vad_threshold,
            "silence_duration_ms": config.server_vad_silence_duration_ms,
            "prefix_padding_ms": config.server_vad_prefix_padding_ms,
            "create_response": config.vad_create_response,
            "interrupt_response": config.vad_interrupt_response,
        }
    else:
        turn_detection = None

    transcription = {"model": config.transcription_model}
    if config.transcription_language:
        transcription["language"] = config.transcription_language
    if config.transcription_prompt:
        transcription["prompt"] = config.transcription_prompt

    audio_input: dict[str, Any] = {
        "transcription": transcription,
        "turn_detection": turn_detection,
    }
    if config.noise_reduction:
        audio_input["noise_reduction"] = {"type": config.noise_reduction}

    audio_output: dict[str, Any] = {"voice": config.voice}
    if config.speed != 1.0:
        audio_output["speed"] = config.speed

    session: dict[str, Any] = {
        "type": "realtime",
        "model": model,
        "output_modalities": ["audio"],
        "audio": {
            "input": audio_input,
            "output": audio_output,
        },
    }

    if config.max_response_output_tokens:
        try:
            value = config.max_response_output_tokens.strip().lower()
            session["max_output_tokens"] = (
                "inf" if value in {"inf", "-1"} else int(value)
            )
        except (ValueError, TypeError):
            pass

    if config.system_instructions:
        session["instructions"] = config.system_instructions

    if config.tool_specs:
        session["tools"] = config.tool_specs
        session["tool_choice"] = "auto"

    if config.truncation_strategy == "disabled":
        session["truncation"] = "disabled"
    elif config.truncation_strategy == "retention_ratio":
        truncation: dict[str, Any] = {
            "type": "retention_ratio",
            "retention_ratio": config.truncation_retention_ratio,
        }
        if config.truncation_token_limit:
            try:
                truncation["token_limits"] = {
                    "post_instructions": int(config.truncation_token_limit)
                }
            except (ValueError, TypeError):
                pass
        session["truncation"] = truncation
    else:
        session["truncation"] = "auto"

    return {
        "session": session,
        "expires_after": {"anchor": "created_at", "seconds": 7200},
    }


async def mint_realtime_client_secret(
    api_key: str,
    base_url: str,
    config: SessionConfig,
    model: str,
    ttl_seconds: int = 7200,
) -> dict:
    """Mint an ephemeral client secret via POST /v1/realtime/client_secrets."""
    body = build_ephemeral_key_body(config, model)
    body["expires_after"]["seconds"] = ttl_seconds

    post_url = f"{base_url}/realtime/client_secrets"
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as http:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        response = await http.post(
            url=post_url,
            json=body,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        if response.status >= 400:
            error_body = await response.text()
            error_preview = (
                f"{error_body[:500]}..." if len(error_body) > 500 else error_body
            )
            log.error(
                f"mint_realtime_client_secret failed: {response.status} {error_preview}"
            )
            response.raise_for_status()
        data = await response.json()

    session_resp = data.get("session", {})
    client_secret = session_resp.get("client_secret", {})
    if isinstance(client_secret, dict) and client_secret.get("value"):
        value = client_secret["value"]
        token_expires_at = client_secret.get("expires_at", 0)
    else:
        value = data.get("value", "")
        token_expires_at = data.get("expires_at", 0)

    result = {
        "value": value,
        "secret_expires_at": data.get("expires_at", 0),
        "token_expires_at": token_expires_at,
        "session": session_resp,
    }
    return result
