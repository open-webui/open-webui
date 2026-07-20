"""orjson-backed rendering for starlette/FastAPI JSON responses."""

from __future__ import annotations

import json
from typing import Any

import orjson
from starlette.responses import JSONResponse


def _orjson_render(self, content: Any) -> bytes:
    try:
        return orjson.dumps(content)
    except (TypeError, ValueError):
        # Match starlette's JSONResponse.render exactly for anything orjson
        # rejects (e.g. non-str dict keys, ints beyond 64 bits).
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
        ).encode('utf-8')


def apply_orjson_response_render() -> None:
    """Serialize every ``JSONResponse`` with orjson instead of the stdlib.

    Overriding ``JSONResponse.render`` is deliberately preferred over
    ``FastAPI(default_response_class=...)``: setting any explicit default —
    even the stdlib ``JSONResponse`` — replaces the route-level
    ``DefaultPlaceholder`` and thereby disables FastAPI's fast path that
    serializes ``response_model`` routes straight to JSON bytes in Pydantic's
    Rust core.  The override leaves that fast path untouched and also covers
    explicit ``JSONResponse(...)`` returns, which a default response class
    would not.

    Output is byte-identical to starlette's stdlib rendering (compact
    separators, raw UTF-8) with one exception: ``NaN``/``Infinity`` floats
    serialize as ``null`` instead of raising (starlette renders with
    ``allow_nan=False``, so today such payloads are a 500 error).
    """
    JSONResponse.render = _orjson_render
