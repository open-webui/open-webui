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
        # Fallback matches starlette's JSONResponse.render exactly.
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
        ).encode('utf-8')


def apply_orjson_response_render() -> None:
    """Serialize every ``JSONResponse`` with orjson instead of the stdlib.

    Deliberately not ``FastAPI(default_response_class=...)``: any explicit
    default replaces the route-level ``DefaultPlaceholder``, which disables
    FastAPI's fast path serializing ``response_model`` routes straight to
    JSON bytes in Pydantic's Rust core.  This override keeps that fast path
    and also covers explicit ``JSONResponse(...)`` returns.

    Only observable change: ``NaN``/``Infinity`` floats serialize as
    ``null`` instead of raising, matching what Pydantic already does on
    ``response_model`` routes.
    """
    JSONResponse.render = _orjson_render
