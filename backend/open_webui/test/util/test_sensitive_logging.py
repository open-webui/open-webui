"""
OBS-10 review follow-ups: tool output, bound tool context and OAuth callback
error values must not reach logs, and logging must not break tool isolation.
"""

import asyncio
import contextlib
import io
import json
import logging
import sys
import types

import pytest

sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))

# Import before any capture is installed: env.py reconfigures root logging with force=True.
from authlib.integrations.base_client.errors import OAuthError  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from open_webui.utils import middleware  # noqa: E402
from open_webui.utils import oauth as oauth_module  # noqa: E402
from open_webui.utils.tools import apply_extra_params_to_tool_function  # noqa: E402

CANARY_PROMPT = "CANARY-PROMPT-1b9e-do-not-log"
CANARY_EMAIL = "canary.user.5d2c@example.invalid"
CANARY_TOOL_RESULT = "CANARY-TOOL-RESULT-77aa-do-not-log"
CANARY_OAUTH_ERROR = "CANARY-OAUTH-ERROR-3f01-do-not-log"


@contextlib.contextmanager
def capture_logs(*loggers):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    saved = [(lg, lg.level) for lg in (root, *loggers)]
    for lg, _ in saved:
        lg.setLevel(logging.DEBUG)
    root.addHandler(handler)
    try:
        yield stream
    finally:
        root.removeHandler(handler)
        for lg, level in saved:
            lg.setLevel(level)


def _assert_absent(output, *canaries):
    for canary in canaries:
        assert canary not in output, f"canary {canary!r} leaked to log output"


def _run_tools_handler(monkeypatch, tool_calls):
    calls = []

    async def echo(text: str, __messages__=None, __user__=None):
        calls.append(text)
        return CANARY_TOOL_RESULT

    extra_params = {
        "__messages__": [{"role": "user", "content": CANARY_PROMPT}],
        "__user__": {"id": "user-1", "email": CANARY_EMAIL},
    }
    tool_entry = {
        "toolkit_id": "kit",
        "callable": apply_extra_params_to_tool_function(echo, extra_params),
        "spec": {
            "name": "echo",
            "parameters": {"properties": {"text": {"type": "string"}}},
        },
        "file_handler": False,
        "citation": True,
    }
    tools = {"echo": tool_entry, "broken": {**tool_entry}}

    async def fake_get_tools_async(*args, **kwargs):
        return tools

    async def fake_generate_chat_completion(request, form_data, user):
        return {"choices": [{"message": {"content": json.dumps(tool_calls)}}]}

    monkeypatch.setattr(middleware, "get_task_model_id", lambda *a, **k: "task")
    monkeypatch.setattr(middleware, "get_tools_async", fake_get_tools_async)
    monkeypatch.setattr(
        middleware, "generate_chat_completion", fake_generate_chat_completion
    )

    request = types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                config=types.SimpleNamespace(
                    TASK_MODEL="",
                    TASK_MODEL_EXTERNAL="",
                    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE="",
                )
            )
        )
    )
    body = {
        "model": "chat-model",
        "messages": [{"role": "user", "content": CANARY_PROMPT}],
        "metadata": {"tool_ids": ["kit"]},
    }

    with capture_logs(middleware.log) as stream:
        _, flags = asyncio.run(
            middleware.chat_completion_tools_handler(
                request, body, types.SimpleNamespace(id="user-1"), {"task": {}}, {}
            )
        )
    return calls, flags, stream.getvalue()


def test_tool_output_and_bound_context_not_logged(monkeypatch):
    calls, flags, output = _run_tools_handler(
        monkeypatch, [{"name": "echo", "parameters": {"text": "hello"}}]
    )

    assert calls == ["hello"]
    assert flags["sources"][0]["document"] == [CANARY_TOOL_RESULT]
    assert "tool_contexts: 1 sources" in output
    _assert_absent(output, CANARY_TOOL_RESULT, CANARY_PROMPT, CANARY_EMAIL)


def test_invalid_tool_parameters_do_not_abort_later_tool_calls(monkeypatch):
    calls, flags, output = _run_tools_handler(
        monkeypatch,
        [
            {"name": "broken", "parameters": None},
            {"name": "echo", "parameters": {"text": "after-broken"}},
        ],
    )

    assert calls == ["after-broken"]
    assert len(flags["sources"]) == 2
    assert "params=NoneType" in output
    _assert_absent(output, CANARY_TOOL_RESULT, CANARY_PROMPT, CANARY_EMAIL)


@pytest.mark.parametrize(
    "error_code, expected",
    [(CANARY_OAUTH_ERROR, "other"), ("access_denied", "access_denied")],
)
def test_oauth_callback_error_code_is_allowlisted(monkeypatch, error_code, expected):
    class FakeClient:
        async def authorize_access_token(self, request):
            raise OAuthError(error=error_code, description=CANARY_OAUTH_ERROR)

    monkeypatch.setattr(oauth_module, "OAUTH_PROVIDERS", {"fake": {}})
    manager = oauth_module.OAuthManager.__new__(oauth_module.OAuthManager)
    manager.get_client = lambda provider: FakeClient()

    with capture_logs(oauth_module.log) as stream:
        with pytest.raises(HTTPException):
            asyncio.run(manager.handle_callback("fake", None, None))

    output = stream.getvalue()
    assert f"OAuth callback error: OAuthError {expected}" in output
    _assert_absent(output, CANARY_OAUTH_ERROR)
