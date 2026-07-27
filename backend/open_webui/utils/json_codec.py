"""The app-wide JSON codec, selected by the ``ENABLE_ORJSON`` env var.

Every module that would otherwise reach for stdlib ``json`` imports ``JSONCodec``
from here, so the whole app switches implementation from a single flag. With the
flag off these are stdlib ``json`` and engineio's codec verbatim, so the default
behaviour is exactly what it was before orjson entered the picture.
"""

from __future__ import annotations

import json as stdlib_json

from engineio import json as engineio_json

from open_webui.env import ENABLE_ORJSON

if ENABLE_ORJSON:
    import orjson

    class ORJSONCodec:
        """stdlib-``json``-compatible codec backed by orjson.

        Anything orjson rejects (non-str dict keys, ints beyond 64 bits, ``NaN``
        literals) falls back to engineio's stdlib-based codec, which keeps its
        oversized-integer guard for untrusted client payloads.
        """

        JSONDecodeError = engineio_json.JSONDecodeError

        @staticmethod
        def dumps(obj, *args, **kwargs):
            try:
                return orjson.dumps(obj).decode('utf-8')
            except (TypeError, ValueError):
                return engineio_json.dumps(obj, *args, **kwargs)

        @staticmethod
        def loads(s, *args, **kwargs):
            try:
                return orjson.loads(s)
            except (TypeError, ValueError):
                return engineio_json.loads(s, *args, **kwargs)

    # Drop-in for stdlib ``json``: ``JSONCodec.dumps`` / ``JSONCodec.loads``.
    JSONCodec = ORJSONCodec
    # Codec handed to the socket.io/engineio managers, which default to their own.
    SOCKETIO_JSON = ORJSONCodec
else:
    JSONCodec = stdlib_json
    SOCKETIO_JSON = engineio_json
