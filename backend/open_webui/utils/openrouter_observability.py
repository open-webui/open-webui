from __future__ import annotations

import os
from typing import Any, Protocol


class ObservabilityAdapter(Protocol):
    def on_request_start(self, trace: dict[str, Any]) -> None: ...

    def on_request_end(self, trace: dict[str, Any]) -> None: ...

    def on_request_error(self, trace: dict[str, Any], error: str) -> None: ...


class NoopObservabilityAdapter:
    def on_request_start(self, trace: dict[str, Any]) -> None:
        return None

    def on_request_end(self, trace: dict[str, Any]) -> None:
        return None

    def on_request_error(self, trace: dict[str, Any], error: str) -> None:
        return None


class InMemoryObservabilityAdapter:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def on_request_start(self, trace: dict[str, Any]) -> None:
        self.events.append({"event": "start", **trace})

    def on_request_end(self, trace: dict[str, Any]) -> None:
        self.events.append({"event": "end", **trace})

    def on_request_error(self, trace: dict[str, Any], error: str) -> None:
        self.events.append({"event": "error", "error": error, **trace})


def get_observability_adapter() -> ObservabilityAdapter:
    adapter_type = os.getenv("OPENROUTER_OBSERVABILITY_ADAPTER", "noop").lower()
    if adapter_type == "memory":
        return InMemoryObservabilityAdapter()
    return NoopObservabilityAdapter()
