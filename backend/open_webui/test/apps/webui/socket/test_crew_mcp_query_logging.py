"""
OBS-10: the crew-mcp-query socket handler must not log prompt text or Graph
token fragments at any level, including on the exception path.
"""

import asyncio
import io
import logging
import sys
import types

import pytest

# Prevent uvicorn import errors in test environment
sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))

# Import before any capture is installed: env.py reconfigures root logging with force=True.
from open_webui.socket import main as socket_main  # noqa: E402

CANARY_PROMPT = "CANARY-PROMPT-7f3a9c1e-do-not-log"
CANARY_TOKEN = "eyJCANARYTOKEN.b81d4e2f0a6c.do-not-log-signature"
SID = "sid-canary"


class FakeSio:
    def __init__(self):
        self.emitted = []

    async def emit(self, event, data=None, room=None, **kwargs):
        self.emitted.append((event, data, room))


class FakeCrewManager:
    def __init__(self, raise_error=False):
        self.raise_error = raise_error
        self.tokens_seen = []
        self.azure_config = types.SimpleNamespace(deployment=None)

    def set_user_token(self, token):
        self.tokens_seen.append(token)

    def get_available_tools(self):
        return [{"name": "fake_tool"}]

    def run_intelligent_crew(self, query, selected_tools):
        if self.raise_error:
            raise RuntimeError(f"provider rejected prompt: {query}")
        return (f"answer to {query}", {}, None)


def _run_handler(monkeypatch, manager):
    fake_sio = FakeSio()
    monkeypatch.setattr(socket_main, "sio", fake_sio)
    monkeypatch.setattr(
        socket_main,
        "SESSION_POOL",
        {SID: {"id": "user-1", "graph_access_token": CANARY_TOKEN}},
    )
    fake_module = types.ModuleType("mcp_backend.routers.crew_mcp")
    fake_module.crew_mcp_manager = manager
    monkeypatch.setitem(sys.modules, "mcp_backend.routers.crew_mcp", fake_module)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    records = []
    handler.addFilter(lambda record: records.append(record) or True)

    root = logging.getLogger()
    saved_levels = (root.level, socket_main.log.level)
    root.setLevel(logging.DEBUG)
    socket_main.log.setLevel(logging.DEBUG)
    root.addHandler(handler)
    try:
        asyncio.run(
            socket_main.crew_mcp_query(
                SID,
                {
                    "query": CANARY_PROMPT,
                    "model": "gpt-test",
                    "selected_tools": ["fake_tool"],
                    "chat_id": "chat-1",
                },
            )
        )
    finally:
        root.removeHandler(handler)
        root.setLevel(saved_levels[0])
        socket_main.log.setLevel(saved_levels[1])
    return fake_sio, records, stream.getvalue()


def _assert_no_canary(records, output):
    # The formatted output includes exception text and tracebacks when exc_info is set.
    sinks = {
        "formatted output": output,
        "record args": " ".join(repr(r.args) for r in records),
    }
    for sink, text in sinks.items():
        for canary in (CANARY_PROMPT, CANARY_TOKEN, CANARY_TOKEN[:20]):
            assert canary not in text, f"canary leaked to {sink}"


@pytest.mark.parametrize("delegated", ["true", "false"])
def test_crew_mcp_query_does_not_log_prompt_or_token(monkeypatch, delegated):
    monkeypatch.setenv("SHP_USE_DELEGATED_ACCESS", delegated)
    manager = FakeCrewManager()

    fake_sio, records, output = _run_handler(monkeypatch, manager)

    assert any(event == "crew-mcp-result" for event, _, _ in fake_sio.emitted)
    assert records, "no log records captured; test is not exercising the handler"
    _assert_no_canary(records, output)
    assert "query_len=33" in output
    assert "graph_access_token present=True" in output
    if delegated == "true":
        assert manager.tokens_seen == [CANARY_TOKEN]


def test_crew_mcp_query_error_path_does_not_log_prompt(monkeypatch):
    monkeypatch.setenv("SHP_USE_DELEGATED_ACCESS", "true")
    manager = FakeCrewManager(raise_error=True)

    fake_sio, records, output = _run_handler(monkeypatch, manager)

    assert any(event == "crew-mcp-error" for event, _, _ in fake_sio.emitted)
    assert any(r.levelno >= logging.ERROR for r in records)
    _assert_no_canary(records, output)
