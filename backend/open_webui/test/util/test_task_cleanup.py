# Tests validating the shutdown-safe scheduling helper

import asyncio
import logging
import sys

import pytest

from open_webui import tasks as tasks_module


# ---------------------------------------------------------------------------
# 1. Normal loop – coroutine should be scheduled & executed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_safe_create_task_active_loop():
    flag = asyncio.Event()

    async def setter():  # pragma: no cover
        flag.set()

    scheduler = getattr(tasks_module, "_safe_create_task", asyncio.create_task)
    scheduler(setter())
    await asyncio.sleep(0)
    assert flag.is_set()


# ---------------------------------------------------------------------------
# 2. Closed loop – scheduling must not raise RuntimeError (regression case)
# ---------------------------------------------------------------------------


def test_cleanup_scheduling_on_closed_loop(caplog):
    caplog.set_level(logging.ERROR)

    # Capture unraisable exceptions that asyncio reports for closed-loop errors
    captured: list[str] = []

    def _hook(urex):
        captured.append(str(urex.exc_value))

    has_get = hasattr(sys, "get_unraisablehook")
    if has_get:
        old_hook = sys.get_unraisablehook()
        sys.set_unraisablehook(_hook)
    else:
        old_hook = sys.unraisablehook
        sys.unraisablehook = _hook

    try:
        # Close the current loop to mimic application shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.close()

        # Patched code uses _safe_create_task, legacy code falls back to asyncio.create_task
        scheduler = getattr(tasks_module, "_safe_create_task", asyncio.create_task)
        scheduler(tasks_module.cleanup_task(None, "dummy"))
    finally:
        if has_get:
            sys.set_unraisablehook(old_hook)
        else:
            sys.unraisablehook = old_hook

    assert not captured  # no RuntimeError surfaced
    assert not caplog.records  # nothing logged either
