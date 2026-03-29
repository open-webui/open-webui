"""Realtime-specific payload validation and call-aware event helpers."""


import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_MODEL_ID_LENGTH = 512
MAX_SESSION_ID_LENGTH = 255
MAX_CHAT_ID_LENGTH = 512
MAX_CALL_ID_LENGTH = 255
MAX_TERMINAL_ID_LENGTH = 512
MAX_LANGUAGE_LENGTH = 32
MAX_SYSTEM_PROMPT_LENGTH = 32_000
MAX_SDP_OFFER_LENGTH = 200_000
MAX_TOOL_ID_COUNT = 64
MAX_TOOL_ID_LENGTH = 512
MAX_TOOL_SERVER_COUNT = 32
MAX_TOOL_SERVER_JSON_LENGTH = 65_536

ALLOWED_REALTIME_FEATURE_KEYS = {
    "voice",
    "image_generation",
    "code_interpreter",
    "web_search",
    "memory",
}

def normalize_realtime_tool_ids(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("tool_ids must be a list")
    if len(value) > MAX_TOOL_ID_COUNT:
        raise ValueError("tool_ids exceeds maximum count")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("tool_ids items must be strings")
        tool_id = item.strip()
        if not tool_id:
            continue
        if len(tool_id) > MAX_TOOL_ID_LENGTH:
            raise ValueError("tool_ids item exceeds maximum length")
        if tool_id in seen:
            continue
        normalized.append(tool_id)
        seen.add(tool_id)
    return normalized


def normalize_realtime_tool_servers(value: Any) -> list[dict]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("tool_servers must be a list")
    if len(value) > MAX_TOOL_SERVER_COUNT:
        raise ValueError("tool_servers exceeds maximum count")

    normalized: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("tool_servers items must be objects")
        encoded = json.dumps(item, sort_keys=True, separators=(",", ":"), default=str)
        if len(encoded) > MAX_TOOL_SERVER_JSON_LENGTH:
            raise ValueError("tool_servers item exceeds maximum size")
        normalized.append(json.loads(encoded))
    return normalized


def normalize_realtime_features(value: Any) -> dict[str, bool]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("features must be an object")

    normalized: dict[str, bool] = {}
    for key, raw_value in value.items():
        if not isinstance(key, str):
            raise ValueError("features keys must be strings")
        if key not in ALLOWED_REALTIME_FEATURE_KEYS:
            continue
        normalized[key] = bool(raw_value)
    return normalized


def build_realtime_bootstrap_binding(
    *,
    user_id: str,
    sid: str,
    chat_id: str,
    model_id: str,
    tool_ids: Any = None,
    tool_servers: Any = None,
    features: Any = None,
    terminal_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "sid": sid,
        "chat_id": chat_id,
        "model_id": model_id,
        "tool_ids": normalize_realtime_tool_ids(tool_ids),
        "tool_servers": normalize_realtime_tool_servers(tool_servers),
        "features": normalize_realtime_features(features),
        "terminal_id": terminal_id or None,
    }


def realtime_event_payload(
    *,
    call_id: Optional[str] = None,
    voice_session_id: Optional[str] = None,
    generation: Optional[int] = None,
    **fields: Any,
) -> dict[str, Any]:
    payload = dict(fields)
    if isinstance(call_id, str) and call_id:
        payload["callId"] = call_id
    if isinstance(voice_session_id, str) and voice_session_id:
        payload["voiceSessionId"] = voice_session_id
    if isinstance(generation, int) and generation > 0:
        payload["generation"] = generation
    return payload


class RealtimeNegotiateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = Field(..., min_length=1, max_length=MAX_MODEL_ID_LENGTH)
    sdp_offer: str = Field(..., min_length=1, max_length=MAX_SDP_OFFER_LENGTH)
    session_id: str = Field(..., min_length=1, max_length=MAX_SESSION_ID_LENGTH)
    tool_ids: list[str] = Field(default_factory=list)
    tool_servers: list[dict] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)
    terminal_id: Optional[str] = Field(default=None, max_length=MAX_TERMINAL_ID_LENGTH)
    chat_id: Optional[str] = Field(default=None, max_length=MAX_CHAT_ID_LENGTH)
    system_prompt: Optional[str] = Field(default=None, max_length=MAX_SYSTEM_PROMPT_LENGTH)
    language: Optional[str] = Field(default=None, max_length=MAX_LANGUAGE_LENGTH)

    @field_validator("tool_ids", mode="before")
    @classmethod
    def _validate_tool_ids(cls, value: Any) -> list[str]:
        return normalize_realtime_tool_ids(value)

    @field_validator("tool_servers", mode="before")
    @classmethod
    def _validate_tool_servers(cls, value: Any) -> list[dict]:
        return normalize_realtime_tool_servers(value)

    @field_validator("features", mode="before")
    @classmethod
    def _validate_features(cls, value: Any) -> dict[str, bool]:
        return normalize_realtime_features(value)


class RealtimeStartPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    callId: str = Field(..., min_length=1, max_length=MAX_CALL_ID_LENGTH)
    modelId: str = Field(..., min_length=1, max_length=MAX_MODEL_ID_LENGTH)
    chatId: str = Field(..., min_length=1, max_length=MAX_CHAT_ID_LENGTH)
    toolIds: list[str] = Field(default_factory=list)
    toolServers: list[dict] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)
    terminalId: Optional[str] = Field(default=None, max_length=MAX_TERMINAL_ID_LENGTH)

    @field_validator("toolIds", mode="before")
    @classmethod
    def _validate_tool_ids(cls, value: Any) -> list[str]:
        return normalize_realtime_tool_ids(value)

    @field_validator("toolServers", mode="before")
    @classmethod
    def _validate_tool_servers(cls, value: Any) -> list[dict]:
        return normalize_realtime_tool_servers(value)

    @field_validator("features", mode="before")
    @classmethod
    def _validate_features(cls, value: Any) -> dict[str, bool]:
        return normalize_realtime_features(value)


class RealtimeCallPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    callId: str = Field(..., min_length=1, max_length=MAX_CALL_ID_LENGTH)
    voiceSessionId: Optional[str] = Field(default=None, max_length=MAX_SESSION_ID_LENGTH)
    generation: Optional[int] = Field(default=None, ge=0)


class RealtimeSettingsUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    callId: str = Field(..., min_length=1, max_length=MAX_CALL_ID_LENGTH)
    voiceSessionId: Optional[str] = Field(default=None, max_length=MAX_SESSION_ID_LENGTH)
    generation: Optional[int] = Field(default=None, ge=0)
    setting: Literal[
        "voice",
        "speed",
        "vad_type",
        "noise_reduction",
        "max_tokens",
        "context",
    ]
    value: Any
