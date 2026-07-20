"""Shared stdlib-``json``-compatible codec backed by orjson."""

from __future__ import annotations

import orjson
from engineio import json as engineio_json


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
