import asyncio
import pytest

from open_webui.utils.tool_governance import (
    ToolContract,
    ToolGovernanceRunner,
    ToolGovernanceValidator,
)


def test_validator_sanitizes_params_against_spec():
    spec = {
        "parameters": {
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            }
        }
    }

    params = {
        "query": "open webui",
        "limit": 5,
        "ignored": True,
    }

    sanitized = ToolGovernanceValidator.sanitize_params(params, spec)

    assert sanitized == {"query": "open webui", "limit": 5}


def test_runner_executes_direct_tool_via_event_caller():
    async def _run():
        payloads = []

        async def fake_event_caller(payload):
            payloads.append(payload)
            return {"ok": True}

        runner = ToolGovernanceRunner(
            event_caller=fake_event_caller,
            metadata={"session_id": "sess-123"},
        )

        result = await runner.execute(
            contract=ToolContract(
                name="search_web",
                spec={"parameters": {"properties": {"query": {}}}},
                direct=True,
                server={"id": "srv-1"},
            ),
            params={"query": "hello"},
        )

        assert result == {"ok": True}
        assert payloads[0]["type"] == "execute:tool"
        assert payloads[0]["data"]["name"] == "search_web"
        assert payloads[0]["data"]["params"] == {"query": "hello"}
        assert payloads[0]["data"]["session_id"] == "sess-123"

    asyncio.run(_run())


def test_runner_executes_callable_tool_with_transform():
    async def _run():
        async def raw_tool(query, __messages__=None):
            return {"query": query, "messages": __messages__}

        def transform(function):
            async def wrapped(**kwargs):
                kwargs["__messages__"] = ["m1"]
                return await function(**kwargs)

            return wrapped

        runner = ToolGovernanceRunner(event_caller=None, metadata={})

        result = await runner.execute(
            contract=ToolContract(
                name="query_knowledge_files",
                spec={"parameters": {"properties": {"query": {}}}},
                callable=raw_tool,
                direct=False,
            ),
            params={"query": "alpha"},
            callable_transform=transform,
        )

        assert result == {"query": "alpha", "messages": ["m1"]}

    asyncio.run(_run())


def test_validator_rejects_oversized_payload(monkeypatch):
    from open_webui.utils import tool_governance as governance

    monkeypatch.setattr(governance, "TOOL_RUNNER_MAX_PARAM_BYTES", 10)

    spec = {
        "parameters": {
            "properties": {
                "query": {"type": "string"},
            }
        }
    }

    with pytest.raises(ValueError):
        governance.ToolGovernanceValidator.sanitize_params(
            {"query": "this is bigger than ten bytes"}, spec
        )


def test_runner_returns_timeout_error(monkeypatch):
    from open_webui.utils import tool_governance as governance

    monkeypatch.setattr(governance, "TOOL_RUNNER_TIMEOUT_SECONDS", 0)

    async def _run():
        async def slow_tool(query):
            await asyncio.sleep(0.01)
            return {"query": query}

        runner = governance.ToolGovernanceRunner(event_caller=None, metadata={})

        result = await runner.execute(
            contract=governance.ToolContract(
                name="slow_tool",
                spec={"parameters": {"properties": {"query": {}}}},
                callable=slow_tool,
                direct=False,
            ),
            params={"query": "alpha"},
        )

        assert "timed out" in result

    asyncio.run(_run())
