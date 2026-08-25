"""The app-wide JSON codec, selected by the ``ENABLE_ORJSON`` env var.

Every module that would otherwise reach for stdlib ``json`` imports ``JSONCodec``
from here, so the whole app switches implementation from a single flag. With the
flag off these are stdlib ``json`` and engineio's codec verbatim, so the default
behaviour is exactly what it was before orjson entered the picture. ``dumps_bytes``
returns UTF-8 bytes for sinks that re-parse the payload; under orjson it skips
both the str round trip and the line-separator escaping ``dumps`` applies, so
never feed it to line-framed output such as SSE.
"""

from __future__ import annotations

import json as stdlib_json

from engineio import json as engineio_json
from open_webui.env import ENABLE_ORJSON

if ENABLE_ORJSON:
    import orjson

    # Module-level because CPython rebuilds these dicts on every call.
    FAST_PATH_KWARGS = ({'separators': (',', ':')}, {'ensure_ascii': False})

    class ORJSONCodec:
        """stdlib-``json``-compatible codec backed by orjson.

        The fast path is not byte-for-byte stdlib: it is always compact, formats
        floats orjson's way (``1e16``, not ``1e+16``), and is raw UTF-8 apart from
        the three line separators ``dumps`` escapes, so a ``separators`` caller loses
        stdlib's ASCII escaping and an ``ensure_ascii=False`` caller loses its
        spacing. ``dumps`` also serializes ``datetime``/``UUID``/dataclasses that
        stdlib refuses, and encodes ``NaN``/``Infinity`` as ``null``. ``loads``
        decodes integers above ``2**64-1`` or below ``-2**63`` as ``float`` and does
        not enforce engineio's 100-digit integer-literal limit.

        What orjson does reject (non-str dict keys and oversized ints on ``dumps``,
        the ``NaN``/``Infinity`` literals on ``loads``) falls back to engineio's
        stdlib-based codec, and with it stdlib's formatting.
        """

        JSONDecodeError = engineio_json.JSONDecodeError

        @staticmethod
        def dumps(obj, *args, **kwargs):
            if args or (kwargs and kwargs not in FAST_PATH_KWARGS):
                return engineio_json.dumps(obj, *args, **kwargs)
            try:
                serialized = orjson.dumps(obj).decode('utf-8')
            except (TypeError, ValueError):
                return engineio_json.dumps(obj, *args, **kwargs)
            # Raw, these three split an SSE frame reassembled with ``splitlines()``.
            # A dict-table translate walks char by char; chained replace runs on C fast paths.
            if '\u2028' in serialized or '\u2029' in serialized or '\x85' in serialized:
                return serialized.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029').replace('\x85', '\\u0085')
            return serialized

        @staticmethod
        def loads(s, *args, **kwargs):
            if args or kwargs:
                return engineio_json.loads(s, *args, **kwargs)
            try:
                return orjson.loads(s)
            except (TypeError, ValueError):
                return engineio_json.loads(s, *args, **kwargs)

    # Drop-in for stdlib ``json``: ``JSONCodec.dumps`` / ``JSONCodec.loads``.
    JSONCodec = ORJSONCodec
    # Codec handed to the socket.io/engineio managers, which default to their own.
    SOCKETIO_JSON = ORJSONCodec

    def dumps_bytes(obj) -> bytes:
        """JSON as UTF-8 bytes, skipping the str round trip and the escaping ``dumps`` does."""
        try:
            return orjson.dumps(obj)
        except (TypeError, ValueError):
            return engineio_json.dumps(obj).encode('utf-8')
else:
    JSONCodec = stdlib_json
    SOCKETIO_JSON = engineio_json

    def dumps_bytes(obj) -> bytes:
        """JSON as UTF-8 bytes; here simply ``dumps`` encoded."""
        return stdlib_json.dumps(obj).encode('utf-8')
