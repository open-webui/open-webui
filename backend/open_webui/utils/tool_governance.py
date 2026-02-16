import logging
import json
import time
import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from open_webui.env import (
    TOOL_RUNNER_MAX_PARAMS,
    TOOL_RUNNER_MAX_PARAM_BYTES,
    TOOL_RUNNER_TIMEOUT_SECONDS,
)


log = logging.getLogger(__name__)


@dataclass
class ToolContract:
    name: str
    spec: dict
    callable: Optional[Callable[..., Awaitable[Any]]] = None
    tool_type: str = ""
    direct: bool = False
    server: Optional[dict] = None


class ToolGovernanceValidator:
    @staticmethod
    def get_allowed_params(spec: dict) -> set[str]:
        return set(spec.get("parameters", {}).get("properties", {}).keys())

    @classmethod
    def sanitize_params(cls, params: Any, spec: dict) -> dict:
        if not isinstance(params, dict):
            return {}

        allowed_params = cls.get_allowed_params(spec)
        if not allowed_params:
            return {}

        sanitized = {key: value for key, value in params.items() if key in allowed_params}

        if TOOL_RUNNER_MAX_PARAMS is not None and TOOL_RUNNER_MAX_PARAMS >= 0:
            sanitized = dict(list(sanitized.items())[:TOOL_RUNNER_MAX_PARAMS])

        if TOOL_RUNNER_MAX_PARAM_BYTES is not None and TOOL_RUNNER_MAX_PARAM_BYTES > 0:
            size = len(json.dumps(sanitized, ensure_ascii=False, default=str).encode("utf-8"))
            if size > TOOL_RUNNER_MAX_PARAM_BYTES:
                raise ValueError(
                    f"Tool parameters payload too large: {size} bytes (max {TOOL_RUNNER_MAX_PARAM_BYTES})"
                )

        return sanitized


class ToolGovernanceRunner:
    def __init__(self, event_caller: Optional[Callable[..., Awaitable[Any]]], metadata: dict):
        self.event_caller = event_caller
        self.metadata = metadata or {}

    @staticmethod
    def _safe_json(data: dict) -> str:
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception:
            return str(data)

    async def execute(
        self,
        contract: ToolContract,
        params: dict,
        callable_transform: Optional[
            Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]
        ] = None,
    ) -> Any:
        execution_id = str(uuid4())
        started_at = time.perf_counter()

        log.info(
            self._safe_json(
                {
                    "event": "tool_execution_start",
                    "execution_id": execution_id,
                    "tool": contract.name,
                    "tool_type": contract.tool_type or "unknown",
                    "direct": contract.direct,
                    "session_id": self.metadata.get("session_id", None),
                    "param_count": len(params or {}),
                    "param_keys": sorted(list((params or {}).keys())),
                    "timeout_seconds": TOOL_RUNNER_TIMEOUT_SECONDS,
                }
            )
        )

        try:
            if contract.direct:
                if self.event_caller is None:
                    raise RuntimeError("Tool event caller is not available")

                result = await asyncio.wait_for(
                    self.event_caller(
                        {
                            "type": "execute:tool",
                            "data": {
                                "id": execution_id,
                                "name": contract.name,
                                "params": params,
                                "server": contract.server or {},
                                "session_id": self.metadata.get("session_id", None),
                            },
                        }
                    ),
                    timeout=TOOL_RUNNER_TIMEOUT_SECONDS,
                )

                duration_ms = int((time.perf_counter() - started_at) * 1000)
                log.info(
                    self._safe_json(
                        {
                            "event": "tool_execution_success",
                            "execution_id": execution_id,
                            "tool": contract.name,
                            "status": "success",
                            "duration_ms": duration_ms,
                        }
                    )
                )
                return result

            if contract.callable is None:
                raise RuntimeError(f"Tool callable is missing for '{contract.name}'")

            tool_callable = contract.callable
            if callable_transform is not None:
                tool_callable = callable_transform(tool_callable)

            result = await asyncio.wait_for(
                tool_callable(**params),
                timeout=TOOL_RUNNER_TIMEOUT_SECONDS,
            )

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            log.info(
                self._safe_json(
                    {
                        "event": "tool_execution_success",
                        "execution_id": execution_id,
                        "tool": contract.name,
                        "status": "success",
                        "duration_ms": duration_ms,
                    }
                )
            )
            return result

        except asyncio.TimeoutError:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            error = f"Tool execution timed out after {TOOL_RUNNER_TIMEOUT_SECONDS}s"
            log.warning(
                self._safe_json(
                    {
                        "event": "tool_execution_timeout",
                        "execution_id": execution_id,
                        "tool": contract.name,
                        "status": "timeout",
                        "duration_ms": duration_ms,
                        "error": error,
                    }
                )
            )
            return error
        except Exception as e:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            log.error(
                self._safe_json(
                    {
                        "event": "tool_execution_error",
                        "execution_id": execution_id,
                        "tool": contract.name,
                        "status": "error",
                        "duration_ms": duration_ms,
                        "error": str(e),
                    }
                )
            )
            return str(e)
