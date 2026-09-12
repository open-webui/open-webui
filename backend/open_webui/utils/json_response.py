"""orjson-backed JSON parsing/rendering for starlette/FastAPI requests and responses."""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from open_webui.env import ENABLE_ORJSON


def apply_orjson_http_json() -> None:
    """Parse request bodies and serialize ``JSONResponse`` with orjson.

    A no-op unless ``ENABLE_ORJSON`` is set, leaving starlette's own
    stdlib-``json`` implementations untouched.

    Not ``FastAPI(default_response_class=...)`` on purpose: an explicit
    default disables FastAPI's Pydantic direct-to-bytes fast path for
    ``response_model`` routes.  NaN/Infinity floats serialize as ``null``
    instead of raising.
    """
    if not ENABLE_ORJSON:
        return

    import orjson

    def render(self, content: Any) -> bytes:
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

    async def request_json(self) -> Any:
        if not hasattr(self, '_json'):
            body = await self.body()
            try:
                self._json = orjson.loads(body)
            except (TypeError, ValueError):
                # Fallback matches starlette's Request.json exactly, including the
                # json.JSONDecodeError that FastAPI turns into a 422.
                self._json = json.loads(body)
        return self._json

    JSONResponse.render = render
    Request.json = request_json
