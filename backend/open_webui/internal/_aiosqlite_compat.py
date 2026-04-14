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
old `Connection.stop()` API and the modern post-0.20 internals (a
private worker thread fed by an `_tx` queue, gated by a `_running`
flag). The replacement is best-effort: the connection record has
already been removed from the pool by the time this is called, and
aiosqlite's own GC will release the underlying sqlite3 handle. We
nudge the worker (sentinel + `_running = False`) so it doesn't linger
on the queue indefinitely, but we do not raise on failure.

Apply this patch once, at import time, before any async engine is
created. To keep the blast radius small the install is:

  * a no-op if the SQLAlchemy build doesn't ship the affected
    `_terminate_force_close` symbol (older or upstream-fixed
    versions);
  * a no-op if the upstream implementation has already moved off the
    `self._connection.stop` reference — detected by inspecting the
    original source — so a future SQLAlchemy fix isn't shadowed by
    this shim;
  * idempotent so repeated imports don't stack patches.

The caller in `internal.db` only invokes `install()` when the runtime
async URL is sqlite-based, so PostgreSQL / MySQL / etc. deployments
get no global mutation at all.
"""

from __future__ import annotations

import inspect
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

    original = target_cls._terminate_force_close
    if getattr(original, '__open_webui_patched__', False):
        return  # Idempotent — already applied.

    # Only patch the specific buggy implementation. If upstream has
    # changed how `_terminate_force_close` is implemented (no longer
    # touching `self._connection.stop`) defer to whatever they ship.
    try:
        original_source = inspect.getsource(original)
    except (OSError, TypeError):
        original_source = ''
    if 'self._connection.stop' not in original_source:
        return

    def _terminate_force_close(self) -> None:
        """Best-effort force close of an aiosqlite connection.

        The pool has already removed the connection record by the time
        this is called; aiosqlite's own GC will release the underlying
        sqlite3 handle either way. We try to nudge the worker so it
        exits promptly on both the pre-0.18 and post-0.20 internals,
        but we never raise: there is nothing useful for the caller to
        do with a failure here.
        """
        conn = getattr(self, '_connection', None)
        if conn is None:
            return

        # aiosqlite ≤ 0.18 — original public API.
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

        # aiosqlite ≥ 0.20 — the worker thread blocks on `_tx.get()`
        # waiting for callables. Setting `_running = False` alone does
        # not wake it; the queue needs a sentinel push so the loop
        # observes the flag on the next iteration.
        nudged = False
        tx = getattr(conn, '_tx', None)
        if tx is not None:
            try:
                tx.put_nowait((None, None))
                nudged = True
            except Exception:
                log.debug(
                    'aiosqlite worker queue rejected the termination '
                    'sentinel; relying on garbage collection.',
                    exc_info=True,
                )

        if hasattr(conn, '_running'):
            try:
                conn._running = False
                nudged = True
            except Exception:
                log.debug(
                    'Could not flip aiosqlite Connection._running during '
                    'force-close.',
                    exc_info=True,
                )

        if not nudged:
            log.debug(
                'aiosqlite Connection has neither stop(), _tx nor _running; '
                'relying on garbage collection to release the underlying '
                'sqlite3 handle.'
            )

    _terminate_force_close.__open_webui_patched__ = True  # type: ignore[attr-defined]
    target_cls._terminate_force_close = _terminate_force_close
