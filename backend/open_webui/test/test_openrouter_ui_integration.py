import pytest

from open_webui.utils.openrouter_policy import OpenRouterRuntimeConfig, apply_openrouter_policies


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
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_ui_A_preset_changes_model():
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    metadata = {"openrouter": {"preset": "smart"}}

    updated, ctx = apply_openrouter_policies(payload, metadata, _cfg())

    assert ctx["preset"] == "smart"
    assert updated["model"] == "anthropic/claude-sonnet-4.5"


def test_ui_B_streaming_toggle_non_stream_fallback():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "hi"}]}
    metadata = {"openrouter": {"non_stream": True}}

    updated, _ = apply_openrouter_policies(payload, metadata, _cfg(default_stream=True))
    assert updated["stream"] is False


def test_ui_C_structured_output_schema_path():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "json"}]}
    metadata = {
        "openrouter": {
            "json_output": True,
            "json_schema": {
                "name": "ui_schema",
                "schema": {
                    "type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                },
            },
        }
    }

    updated, _ = apply_openrouter_policies(payload, metadata, _cfg())
    assert updated["response_format"]["type"] == "json_schema"
    assert updated["response_format"]["json_schema"]["name"] == "ui_schema"


def test_ui_D_response_healing_enabled_for_json_mode():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "return broken json"}]}
    metadata = {"openrouter": {"json_output": True, "enable_response_healing": True}}

    updated, _ = apply_openrouter_policies(payload, metadata, _cfg())
    assert any(plugin.get("id") == "response-healing" for plugin in updated.get("plugins", []))


def test_ui_E_sensitive_request_enables_zdr():
    payload = {"model": "google/gemini-3-flash-preview", "messages": [{"role": "user", "content": "secret"}]}
    metadata = {"openrouter": {"sensitive": True}}

    updated, _ = apply_openrouter_policies(payload, metadata, _cfg())
    assert updated["provider"]["zdr"] is True


def test_ui_F_guardrails_disallow_model_with_clear_error():
    payload = {
        "model": "anthropic/claude-sonnet-4.5",
        "messages": [{"role": "user", "content": "hi"}],
    }
    metadata = {"openrouter": {"guardrail_allowed_models": ["google/gemini-3-flash-preview"]}}

    with pytest.raises(ValueError, match="allowlist"):
        apply_openrouter_policies(payload, metadata, _cfg())
