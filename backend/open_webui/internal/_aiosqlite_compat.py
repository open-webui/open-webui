"""
Compatibility shim for SQLAlchemy ↔ aiosqlite ≥ 0.20.

Background
----------
SQLAlchemy ≥ 2.0.36 added a `terminate_force_close()` path on its
async DB-API adapters, used by the connection pool when a connection
must be invalidated immediately — typically because the operation it
was running was cancelled (for example, a request was aborted by the
client mid-query).

For the aiosqlite dialect this implementation lives at
`sqlalchemy.dialects.sqlite.aiosqlite.AsyncAdapt_aiosqlite_connection
._terminate_force_close` and unconditionally accesses
`self._connection.stop`. That attribute existed on
`aiosqlite.Connection` in 0.18 and earlier (where Connection
sub-classed `threading.Thread` and exposed a `stop()` method). It was
removed in aiosqlite 0.20 when the worker model was refactored.

The result, on the version combo Open WebUI pins
(SQLAlchemy 2.0.48 + aiosqlite 0.21.0), is that *every* cancellation
mid-DB-call produces a multi-page

    NotImplementedError: terminate_force_close() not implemented by this DBAPI shim

at ERROR level — drowning real errors in noise even though the
underlying connection is being torn down correctly by aiosqlite's own
worker on the next iteration.

Fix
---
Replace `_terminate_force_close` with one that understands both the
old `Connection.stop()` API and the modern internal `_running` flag.
Setting `_running = False` causes the aiosqlite worker thread to
break out of its loop on the next tick, which is the same end-state
the original code was after.

Apply this patch once, at import time, before any async engine is
created. Idempotent and safe to import on systems where the affected
SQLAlchemy/aiosqlite versions are not in use — it bails out silently
if the symbol is missing.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def install() -> None:
    try:
        from sqlalchemy.dialects.sqlite import aiosqlite as _sa_aiosqlite
    except ImportError:
        # SQLAlchemy installed without sqlite+aiosqlite — nothing to patch.
        return

    target_cls = getattr(_sa_aiosqlite, 'AsyncAdapt_aiosqlite_connection', None)
    if target_cls is None or not hasattr(target_cls, '_terminate_force_close'):
        # Either an older SQLAlchemy without the terminate path, or an
        # upstream rewrite that no longer needs this shim.
        return

    if getattr(target_cls._terminate_force_close, '__open_webui_patched__', False):
        return  # Idempotent — already applied.

    def _terminate_force_close(self) -> None:
        conn = getattr(self, '_connection', None)
        if conn is None:
            return

        # aiosqlite ≤ 0.18 — original API.
        stop = getattr(conn, 'stop', None)
        if callable(stop):
            try:
                stop()
            except Exception:
                log.debug(
                    'aiosqlite Connection.stop() raised during force-close; '
                    'connection will be cleaned up by garbage collection.',
                    exc_info=True,
                )
            return

        # aiosqlite ≥ 0.20 — the worker thread observes its own
        # `_running` flag and exits on the next loop tick, releasing
        # the underlying sqlite3 connection.
        if hasattr(conn, '_running'):
            try:
                conn._running = False
            except Exception:
                log.debug(
                    'Could not flip aiosqlite Connection._running during '
                    'force-close; connection will be cleaned up by garbage '
                    'collection.',
                    exc_info=True,
                )
            return

        # Unknown aiosqlite internals — fall back to leaving the
        # connection to garbage collection. Do *not* re-raise: the pool
        # has already removed the connection record and there is
        # nothing useful for the caller to do.
        log.debug(
            'aiosqlite Connection has neither stop() nor _running; relying '
            'on garbage collection to release the underlying sqlite3 handle.'
        )

    _terminate_force_close.__open_webui_patched__ = True  # type: ignore[attr-defined]
    target_cls._terminate_force_close = _terminate_force_close
