from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
import yaml

BACKEND_SRC = Path(__file__).resolve().parents[1]

open_webui_pkg = types.ModuleType("open_webui")
open_webui_pkg.__path__ = [str(BACKEND_SRC / "open_webui")]
sys.modules.setdefault("open_webui", open_webui_pkg)

SETTINGS_PATH = BACKEND_SRC / "open_webui" / "settings.py"
spec = importlib.util.spec_from_file_location("open_webui.settings", SETTINGS_PATH)
if spec is None or spec.loader is None:  # pragma: no cover - defensive guard
    raise RuntimeError("Unable to load open_webui.settings module")
settings_module = importlib.util.module_from_spec(spec)
sys.modules["open_webui.settings"] = settings_module
spec.loader.exec_module(settings_module)


PROFILE_DIR = Path(__file__).resolve().parents[2] / "config" / "profiles"
ENTERPRISE_PROFILE_PATH = PROFILE_DIR / "enterprise.yaml"
FULL_PROFILE_PATH = PROFILE_DIR / "full.yaml"

HEAVY_LOCAL_MODULES = {
    "torch",
    "sentence_transformers",
    "faster_whisper",
    "chromadb",
    "rapidocr",
    "colbert",
    "onnxruntime",
}


def _load_profile(path: Path) -> dict[str, dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _set_profile_environment(
    monkeypatch: pytest.MonkeyPatch, variables: dict[str, object]
) -> None:
    for key in variables:
        monkeypatch.delenv(key, raising=False)

    for key, value in variables.items():
        if isinstance(value, bool):
            monkeypatch.setenv(key, "true" if value else "false")
        else:
            monkeypatch.setenv(key, str(value))


def _reset_settings_cache() -> None:
    settings_module.get_settings.cache_clear()


def test_enterprise_profile_disables_local_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _load_profile(ENTERPRISE_PROFILE_PATH)
    env_values: dict[str, object] = {}
    env_values.update(profile.get("environment", {}))
    env_values.update(profile.get("placeholders", {}))

    _set_profile_environment(monkeypatch, env_values)
    _reset_settings_cache()

    removed_modules = {name: sys.modules.pop(name, None) for name in HEAVY_LOCAL_MODULES}

    cfg = settings_module.Settings()
    assert cfg.enterprise_mode is True
    assert cfg.local_features_enabled is False

    assert cfg.rag_embedding_engine == "openai"
    assert cfg.audio_stt_engine == "openai"
    assert cfg.audio_tts_engine == "openai"
    assert cfg.vector_db == "pgvector"
    assert cfg.ocr_engine == "azure_document_intelligence"
    assert cfg.rag_reranking_engine == "external"

    for module_name in HEAVY_LOCAL_MODULES:
        assert module_name not in sys.modules, f"{module_name} should not be imported in enterprise mode"

    # Restore any previously loaded modules to avoid leaking state to other tests.
    for name, module in removed_modules.items():
        if module is not None:
            sys.modules[name] = module


def test_full_profile_preserves_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _load_profile(FULL_PROFILE_PATH)
    env_values: dict[str, object] = {}
    env_values.update(profile.get("environment", {}))

    _set_profile_environment(monkeypatch, env_values)
    _reset_settings_cache()

    cfg = settings_module.Settings()

    assert cfg.enterprise_mode is False
    assert cfg.local_features_enabled is True
    assert cfg.rag_embedding_engine == "local"
    assert cfg.audio_stt_engine in {"local", "whisper"}
    assert cfg.audio_tts_engine == "local"
    assert cfg.vector_db in {"chroma", "local"}
    assert cfg.ocr_engine in {"local", "rapidocr"}
    assert cfg.bypass_embedding_and_retrieval is False
