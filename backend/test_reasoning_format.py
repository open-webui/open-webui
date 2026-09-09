from __future__ import annotations

import ast
from pathlib import Path


def _load_get_reasoning_format():
    source = Path(__file__).parent.joinpath("open_webui/utils/middleware.py").read_text()
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_reasoning_format"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(module, "middleware.py", "exec"), namespace)
    return namespace["get_reasoning_format"]


get_reasoning_format = _load_get_reasoning_format()


def test_reasoning_replay_preserves_existing_default():
    assert get_reasoning_format({"owned_by": "ollama"}) == "thinking"
    assert get_reasoning_format({"provider": "llama.cpp"}) == "reasoning_content"


def test_reasoning_replay_can_be_disabled_per_model():
    disabled = {"params": {"reinject_reasoning": False}}
    assert get_reasoning_format({**disabled, "owned_by": "ollama"}) is None
    assert get_reasoning_format({**disabled, "provider": "llama.cpp"}) is None


def test_reasoning_replay_can_be_enabled_for_supported_providers():
    enabled = {"params": {"reinject_reasoning": True}}
    assert get_reasoning_format({**enabled, "owned_by": "ollama"}) == "thinking"
    assert get_reasoning_format({**enabled, "provider": "llama.cpp"}) == "reasoning_content"


def test_reasoning_replay_stays_disabled_for_unknown_providers():
    model = {"provider": "openai", "params": {"reinject_reasoning": True}}
    assert get_reasoning_format(model) is None
