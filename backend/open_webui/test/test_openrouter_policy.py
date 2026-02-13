import pytest

from open_webui.utils.openrouter_policy import (
    OpenRouterRuntimeConfig,
    apply_openrouter_policies,
    build_attribution_headers,
    build_prompt_cache_key,
)


def _cfg(**overrides):
    base = OpenRouterRuntimeConfig(
        provider_sort="latency",
        allow_fallbacks=True,
        data_collection="deny",
        enable_sensitive_zdr=True,
        sensitive_metadata_key="sensitive",
        default_stream=True,
        enable_response_healing=True,
        enable_structured_outputs=True,
        prompt_cache_ttl_seconds=60,
        default_preset="fast",
        preset_fast_model="google/gemini-3-flash-preview",
        preset_smart_model="anthropic/claude-sonnet-4.5",
        preset_code_model="openai/gpt-5.2-codex",
        preset_code_temperature=0.1,
        attribution_enabled=True,
        attribution_http_referer="https://openwebui.com/",
        attribution_x_title="Open WebUI",
        guardrail_allowed_models=set(),
        guardrail_allowed_providers=set(),
        guardrail_max_tokens=None,
        guardrail_hard_fail=False,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_provider_sort_and_fallback_defaults():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "hi"}]}
    updated, _ = apply_openrouter_policies(payload, {"provider_sort": "throughput"}, _cfg())

    assert updated["provider"]["sort"] == "throughput"
    assert updated["provider"]["allowFallbacks"] is True
    assert updated["provider"]["dataCollection"] == "deny"


def test_sensitive_requests_enable_zdr_only_when_sensitive():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "hi"}]}

    sensitive_updated, _ = apply_openrouter_policies(payload, {"sensitive": True}, _cfg())
    non_sensitive_updated, _ = apply_openrouter_policies(payload, {"sensitive": False}, _cfg())

    assert sensitive_updated["provider"]["zdr"] is True
    assert "zdr" not in non_sensitive_updated["provider"]


def test_streaming_policy_default_and_fallback_non_stream():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "hi"}]}
    updated_stream, _ = apply_openrouter_policies(payload, {}, _cfg(default_stream=True))
    updated_non_stream, _ = apply_openrouter_policies(payload, {"non_stream": True}, _cfg(default_stream=True))

    assert updated_stream["stream"] is True
    assert updated_non_stream["stream"] is False


def test_structured_output_and_response_healing_for_json_mode():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "return json"}]}
    updated, _ = apply_openrouter_policies(payload, {"json_output": True}, _cfg())

    assert updated["response_format"] == {"type": "json_object"}
    assert any(plugin.get("id") == "response-healing" for plugin in updated.get("plugins", []))


def test_prompt_cache_key_changes_with_schema_and_preset():
    base_payload = {
        "model": "google/gemini-3-flash-preview",
        "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
    }

    key_a = build_prompt_cache_key(base_payload, preset="fast")

    payload_with_schema = {
        **base_payload,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "x", "schema": {"type": "object"}},
        },
    }
    key_b = build_prompt_cache_key(payload_with_schema, preset="fast")
    key_c = build_prompt_cache_key(base_payload, preset="code")

    assert key_a != key_b
    assert key_a != key_c


def test_preset_selection_fast_smart_code():
    payload = {"messages": [{"role": "user", "content": "hi"}]}

    fast_updated, fast_ctx = apply_openrouter_policies(payload, {"preset": "fast"}, _cfg())
    smart_updated, smart_ctx = apply_openrouter_policies(payload, {"preset": "smart"}, _cfg())
    code_updated, code_ctx = apply_openrouter_policies(payload, {"preset": "code"}, _cfg())

    assert fast_ctx["preset"] == "fast"
    assert fast_updated["model"] == "google/gemini-3-flash-preview"

    assert smart_ctx["preset"] == "smart"
    assert smart_updated["model"] == "anthropic/claude-sonnet-4.5"

    assert code_ctx["preset"] == "code"
    assert code_updated["model"] == "openai/gpt-5.2-codex"
    assert code_updated["temperature"] == pytest.approx(0.1)


def test_attribution_headers_enabled_for_openrouter():
    headers = build_attribution_headers(
        "https://openrouter.ai/api/v1/chat/completions",
        {"Content-Type": "application/json"},
        _cfg(),
    )

    assert headers["HTTP-Referer"] == "https://openwebui.com/"
    assert headers["X-Title"] == "Open WebUI"


def test_guardrails_allowlist_and_limits():
    cfg = _cfg(
        guardrail_allowed_models={"google/gemini-3-flash-preview"},
        guardrail_allowed_providers={"openai", "google"},
        guardrail_max_tokens=128,
        guardrail_hard_fail=False,
    )

    payload = {
        "model": "google/gemini-3-flash-preview",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 512,
    }

    updated, _ = apply_openrouter_policies(payload, {}, cfg)

    assert set(updated["provider"]["only"]) == {"openai", "google"}
    assert updated["max_tokens"] == 128
    assert "guardrail_warning" in updated["metadata"]["openrouter"]


def test_guardrails_reject_disallowed_model():
    cfg = _cfg(guardrail_allowed_models={"google/gemini-3-flash-preview"})
    payload = {
        "model": "anthropic/claude-sonnet-4.5",
        "messages": [{"role": "user", "content": "hi"}],
    }

    with pytest.raises(ValueError):
        apply_openrouter_policies(payload, {}, cfg)


def test_guardrails_hard_fail_on_token_limit():
    cfg = _cfg(guardrail_max_tokens=64, guardrail_hard_fail=True)
    payload = {
        "model": "google/gemini-3-flash-preview",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 128,
    }

    with pytest.raises(ValueError):
        apply_openrouter_policies(payload, {}, cfg)
