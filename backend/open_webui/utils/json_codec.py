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

    # orjson emits these raw and Python treats all three as line boundaries: one raw
    # separator splits an SSE frame reassembled with ``splitlines()``. Escaped even
    # where stdlib would not.
    LINE_SEPARATOR_ESCAPES = str.maketrans({'\u2028': '\\u2028', '\u2029': '\\u2029', '\x85': '\\u0085'})

    # Module-level because CPython rebuilds these dicts on every call.
    FAST_PATH_KWARGS = ({'separators': (',', ':')}, {'ensure_ascii': False})

    class ORJSONCodec:
        """stdlib-``json``-compatible codec backed by orjson.

        The fast path is not byte-for-byte stdlib: it is always compact, formats
        floats orjson's way (``1e16``, not ``1e+16``), and is raw UTF-8 apart from
        the three line separators escaped above, so a ``separators`` caller loses
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
            if '\u2028' in serialized or '\u2029' in serialized or '\x85' in serialized:
                return serialized.translate(LINE_SEPARATOR_ESCAPES)
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
else:
    JSONCodec = stdlib_json
    SOCKETIO_JSON = engineio_json
