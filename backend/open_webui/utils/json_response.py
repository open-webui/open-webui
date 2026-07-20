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

    Not ``FastAPI(default_response_class=...)`` on purpose: an explicit
    default disables FastAPI's Pydantic direct-to-bytes fast path for
    ``response_model`` routes.  NaN/Infinity floats now serialize as
    ``null`` instead of raising.
    """
    JSONResponse.render = _orjson_render
