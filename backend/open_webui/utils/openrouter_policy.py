from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any


_ALLOWED_SORTS = {"latency", "price", "throughput"}
_PROMPT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(slots=True)
class OpenRouterRuntimeConfig:
    provider_sort: str
    allow_fallbacks: bool
    data_collection: str
    enable_sensitive_zdr: bool
    sensitive_metadata_key: str
    default_stream: bool
    enable_response_healing: bool
    enable_structured_outputs: bool
    prompt_cache_ttl_seconds: int
    default_preset: str
    preset_fast_model: str
    preset_smart_model: str
    preset_code_model: str
    preset_code_temperature: float
    attribution_enabled: bool
    attribution_http_referer: str
    attribution_x_title: str
    guardrail_allowed_models: set[str]
    guardrail_allowed_providers: set[str]
    guardrail_max_tokens: int | None
    guardrail_hard_fail: bool

    @classmethod
    def from_env(cls) -> "OpenRouterRuntimeConfig":
        max_tokens = os.getenv("OPENROUTER_GUARDRAIL_MAX_TOKENS", "").strip()
        max_tokens_value = int(max_tokens) if max_tokens.isdigit() else None

        allowed_models = {
            model.strip()
            for model in os.getenv("OPENROUTER_GUARDRAIL_ALLOWED_MODELS", "").split(",")
            if model.strip()
        }
        allowed_providers = {
            provider.strip()
            for provider in os.getenv("OPENROUTER_GUARDRAIL_ALLOWED_PROVIDERS", "").split(",")
            if provider.strip()
        }

        provider_sort = os.getenv("OPENROUTER_PROVIDER_SORT", "latency").strip().lower()
        if provider_sort not in _ALLOWED_SORTS:
            provider_sort = "latency"

        return cls(
            provider_sort=provider_sort,
            allow_fallbacks=os.getenv("OPENROUTER_PROVIDER_ALLOW_FALLBACKS", "true").lower()
            == "true",
            data_collection=os.getenv("OPENROUTER_DATA_COLLECTION", "deny").lower(),
            enable_sensitive_zdr=os.getenv("OPENROUTER_ENABLE_SENSITIVE_ZDR", "true").lower()
            == "true",
            sensitive_metadata_key=os.getenv("OPENROUTER_SENSITIVE_KEY", "sensitive"),
            default_stream=os.getenv("OPENROUTER_DEFAULT_STREAM", "true").lower() == "true",
            enable_response_healing=os.getenv("OPENROUTER_ENABLE_RESPONSE_HEALING", "true").lower()
            == "true",
            enable_structured_outputs=os.getenv("OPENROUTER_ENABLE_STRUCTURED_OUTPUTS", "true").lower()
            == "true",
            prompt_cache_ttl_seconds=int(os.getenv("OPENROUTER_PROMPT_CACHE_TTL_SECONDS", "300")),
            default_preset=os.getenv("OPENROUTER_DEFAULT_PRESET", "fast").strip().lower(),
            preset_fast_model=os.getenv("OPENROUTER_PRESET_FAST_MODEL", "google/gemini-3-flash-preview"),
            preset_smart_model=os.getenv("OPENROUTER_PRESET_SMART_MODEL", "anthropic/claude-sonnet-4.5"),
            preset_code_model=os.getenv("OPENROUTER_PRESET_CODE_MODEL", "openai/gpt-5.2-codex"),
            preset_code_temperature=float(os.getenv("OPENROUTER_PRESET_CODE_TEMPERATURE", "0.1")),
            attribution_enabled=os.getenv("OPENROUTER_ENABLE_ATTRIBUTION_HEADERS", "true").lower()
            == "true",
            attribution_http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "https://openwebui.com/"),
            attribution_x_title=os.getenv("OPENROUTER_X_TITLE", "Open WebUI"),
            guardrail_allowed_models=allowed_models,
            guardrail_allowed_providers=allowed_providers,
            guardrail_max_tokens=max_tokens_value,
            guardrail_hard_fail=os.getenv("OPENROUTER_GUARDRAIL_HARD_FAIL", "false").lower() == "true",
        )


def _normalize_sort(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    normalized = value.lower()
    return normalized if normalized in _ALLOWED_SORTS else fallback


def _get_metadata_value(metadata: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(metadata, dict):
        return default

    if key in metadata:
        return metadata.get(key)

    nested = metadata.get("openrouter")
    if isinstance(nested, dict) and key in nested:
        return nested.get(key)

    return default


def _is_sensitive(metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig) -> bool:
    if not metadata:
        return False
    return bool(_get_metadata_value(metadata, cfg.sensitive_metadata_key, False))


def _extract_system_prompt(payload: dict[str, Any]) -> str:
    messages = payload.get("messages") or []
    for message in messages:
        if message.get("role") in {"system", "developer"}:
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [p.get("text", "") for p in content if p.get("type") == "text"]
                return "\n".join([t for t in texts if t])
    return ""


def _schema_fingerprint(payload: dict[str, Any]) -> str:
    response_format = payload.get("response_format")
    if not response_format:
        return ""
    serialized = json.dumps(response_format, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_prompt_cache_key(payload: dict[str, Any], preset: str) -> str:
    cache_input = {
        "model": payload.get("model"),
        "preset": preset,
        "system_prompt": _extract_system_prompt(payload),
        "schema_hash": _schema_fingerprint(payload),
    }
    serialized = json.dumps(cache_input, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def apply_prompt_cache_metadata(payload: dict[str, Any], cache_key: str, ttl_seconds: int) -> bool:
    now = time.time()
    entry = _PROMPT_CACHE.get(cache_key)

    hit = False
    if entry and entry[0] > now:
        hit = True
    else:
        _PROMPT_CACHE[cache_key] = (
            now + max(ttl_seconds, 1),
            {
                "cache_key": cache_key,
                "created_at": int(now),
            },
        )

    metadata = payload.setdefault("metadata", {})
    metadata.setdefault("openrouter", {})
    metadata["openrouter"]["prompt_cache"] = {
        "key": cache_key,
        "hit": hit,
        "ttl_seconds": ttl_seconds,
    }
    return hit


def _apply_preset(payload: dict[str, Any], metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig) -> str:
    preset = _get_metadata_value(metadata, "preset", None) or payload.pop("preset", None) or cfg.default_preset
    preset = str(preset).lower().strip()

    if preset == "smart":
        payload.setdefault("model", cfg.preset_smart_model)
    elif preset == "code":
        payload.setdefault("model", cfg.preset_code_model)
        payload.setdefault("temperature", cfg.preset_code_temperature)
        payload.setdefault("top_p", 1)
    else:
        preset = "fast"
        payload.setdefault("model", cfg.preset_fast_model)

    return preset


def _apply_provider_policy(
    payload: dict[str, Any], metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig
) -> None:
    provider = payload.setdefault("provider", {})

    requested_sort = _get_metadata_value(metadata, "provider_sort", None)

    provider["sort"] = _normalize_sort(
        str(requested_sort) if requested_sort else provider.get("sort"),
        cfg.provider_sort,
    )
    provider["allowFallbacks"] = bool(cfg.allow_fallbacks)
    provider["dataCollection"] = "deny"

    if cfg.enable_sensitive_zdr and _is_sensitive(metadata, cfg):
        provider["zdr"] = True


def _apply_streaming_policy(
    payload: dict[str, Any], metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig
) -> None:
    if _get_metadata_value(metadata, "non_stream", False) is True:
        payload["stream"] = False
        return

    if "stream" not in payload and cfg.default_stream:
        payload["stream"] = True


def _apply_structured_output_and_healing(
    payload: dict[str, Any], metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig
) -> None:
    metadata = metadata or {}
    wants_json = bool(_get_metadata_value(metadata, "json_output", False)) or bool(payload.get("response_format"))

    if wants_json and cfg.enable_structured_outputs and "response_format" not in payload:
        json_schema = _get_metadata_value(metadata, "json_schema", None)
        if isinstance(json_schema, dict):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema.get("name", "response"),
                    "strict": bool(_get_metadata_value(metadata, "json_strict", True)),
                    "schema": json_schema.get("schema", {}),
                },
            }
        else:
            payload["response_format"] = {"type": "json_object"}

    enable_healing = bool(
        _get_metadata_value(metadata, "enable_response_healing", cfg.enable_response_healing)
    )
    if wants_json and enable_healing:
        plugins = payload.setdefault("plugins", [])
        if not any(plugin.get("id") == "response-healing" for plugin in plugins if isinstance(plugin, dict)):
            plugins.append({"id": "response-healing"})


def _enforce_guardrails(
    payload: dict[str, Any], metadata: dict[str, Any] | None, cfg: OpenRouterRuntimeConfig
) -> None:
    metadata = metadata or {}

    requested_allowed_models = _get_metadata_value(metadata, "guardrail_allowed_models", None)
    requested_allowed_providers = _get_metadata_value(metadata, "guardrail_allowed_providers", None)
    requested_max_tokens = _get_metadata_value(metadata, "guardrail_max_tokens", None)
    requested_hard_fail = _get_metadata_value(metadata, "guardrail_hard_fail", None)

    guardrail_allowed_models = cfg.guardrail_allowed_models
    if isinstance(requested_allowed_models, list):
        guardrail_allowed_models = {
            str(model).strip() for model in requested_allowed_models if str(model).strip()
        }

    guardrail_allowed_providers = cfg.guardrail_allowed_providers
    if isinstance(requested_allowed_providers, list):
        guardrail_allowed_providers = {
            str(provider).strip()
            for provider in requested_allowed_providers
            if str(provider).strip()
        }

    guardrail_max_tokens = cfg.guardrail_max_tokens
    if isinstance(requested_max_tokens, int):
        guardrail_max_tokens = requested_max_tokens

    guardrail_hard_fail = cfg.guardrail_hard_fail
    if isinstance(requested_hard_fail, bool):
        guardrail_hard_fail = requested_hard_fail

    model = payload.get("model")
    if guardrail_allowed_models and model and model not in guardrail_allowed_models:
        raise ValueError(f"Model '{model}' is not in OpenRouter allowlist")

    provider = payload.setdefault("provider", {})

    if guardrail_allowed_providers:
        if provider.get("only"):
            requested = set(provider.get("only", []))
            if not requested.issubset(guardrail_allowed_providers):
                raise ValueError("Requested providers violate OpenRouter provider allowlist")
        else:
            provider["only"] = sorted(guardrail_allowed_providers)

    max_tokens = payload.get("max_tokens") or payload.get("max_completion_tokens")
    if guardrail_max_tokens and isinstance(max_tokens, int) and max_tokens > guardrail_max_tokens:
        if guardrail_hard_fail:
            raise ValueError(
                f"max_tokens {max_tokens} exceeds guardrail limit {guardrail_max_tokens}"
            )

        payload["max_tokens"] = guardrail_max_tokens
        metadata = payload.setdefault("metadata", {})
        metadata.setdefault("openrouter", {})
        metadata["openrouter"]["guardrail_warning"] = (
            f"max_tokens reduced to {guardrail_max_tokens}"
        )


def build_attribution_headers(
    url: str, headers: dict[str, str], cfg: OpenRouterRuntimeConfig
) -> dict[str, str]:
    if not cfg.attribution_enabled or "openrouter.ai" not in url:
        return headers

    merged = {**headers}
    if cfg.attribution_http_referer:
        merged["HTTP-Referer"] = cfg.attribution_http_referer
    if cfg.attribution_x_title:
        merged["X-Title"] = cfg.attribution_x_title
    return merged


def apply_openrouter_policies(
    payload: dict[str, Any],
    metadata: dict[str, Any] | None,
    cfg: OpenRouterRuntimeConfig,
) -> tuple[dict[str, Any], dict[str, Any]]:
    updated_payload = {**payload}

    preset = _apply_preset(updated_payload, metadata, cfg)
    _apply_provider_policy(updated_payload, metadata, cfg)
    _apply_streaming_policy(updated_payload, metadata, cfg)
    _apply_structured_output_and_healing(updated_payload, metadata, cfg)
    _enforce_guardrails(updated_payload, metadata, cfg)

    cache_key = build_prompt_cache_key(updated_payload, preset)
    cache_hit = apply_prompt_cache_metadata(
        updated_payload,
        cache_key=cache_key,
        ttl_seconds=cfg.prompt_cache_ttl_seconds,
    )

    return updated_payload, {
        "preset": preset,
        "cache_key": cache_key,
        "cache_hit": cache_hit,
    }
