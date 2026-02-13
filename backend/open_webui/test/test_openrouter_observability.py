from open_webui.utils.openrouter_observability import InMemoryObservabilityAdapter


def test_observability_adapter_invocation_without_side_effects():
    adapter = InMemoryObservabilityAdapter()
    trace = {"model": "google/gemini-3-flash-preview", "user_id": "u1"}

    adapter.on_request_start(trace)
    adapter.on_request_end(trace)
    adapter.on_request_error(trace, "boom")

    assert len(adapter.events) == 3
    assert adapter.events[0]["event"] == "start"
    assert adapter.events[1]["event"] == "end"
    assert adapter.events[2]["event"] == "error"
    assert adapter.events[2]["error"] == "boom"
