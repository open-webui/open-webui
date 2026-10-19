"""Cooperative cancellation for long-running file processing.

A knowledge file can spend minutes (sometimes hours) in content extraction and
embedding.  When a user deletes such a file while it is still being processed,
the delete has to take effect immediately and the background pipeline has to
stop instead of writing vectors and status updates for a file that no longer
exists.

Two mechanisms cooperate here:

* an in-process registry of ``asyncio.Event`` objects, so a delete served by
  this worker interrupts the pipeline within ``POLL_INTERVAL`` seconds — even
  while it is blocked waiting on a loader thread, and
* a database fallback (the file row is gone, or carries ``status: cancelled``)
  which also covers a delete served by a different worker process.

Nothing here can abort a blocking third-party call: a Docling conversion keeps
running in its worker thread until the remote server answers.  What the
pipeline does is stop waiting for it and discard the result, which is what the
user actually observes.
"""

import asyncio
import logging
from typing import Awaitable, TypeVar

from open_webui.internal.db import get_async_db_context
from open_webui.models.files import Files

log = logging.getLogger(__name__)

T = TypeVar('T')

# How often a cancellable wait wakes up to look for a cancellation request, and
# how many of those ticks pass before the (more expensive) database fallback is
# consulted.
POLL_INTERVAL = 5.0
DB_POLL_EVERY = 6

_cancel_events: dict[str, asyncio.Event] = {}
# How many nested/parallel jobs share an event. The upload background task and a
# concurrent POST /file/add can both be working on the same file; the signal has
# to survive until the last of them is done with it.
_registrations: dict[str, int] = {}


class FileProcessingCancelled(Exception):
    """Raised inside the processing pipeline once a delete request arrives."""

    def __init__(self, file_id: str):
        self.file_id = file_id
        super().__init__(f'Processing of file {file_id} was cancelled')


def register_processing(file_id: str) -> asyncio.Event:
    """Announce that `file_id` is being processed by this worker."""
    event = _cancel_events.get(file_id)
    if event is None:
        event = asyncio.Event()
        _cancel_events[file_id] = event
    _registrations[file_id] = _registrations.get(file_id, 0) + 1
    return event


def unregister_processing(file_id: str) -> None:
    remaining = _registrations.get(file_id, 0) - 1
    if remaining > 0:
        _registrations[file_id] = remaining
        return

    _registrations.pop(file_id, None)
    _cancel_events.pop(file_id, None)


def request_cancellation(file_id: str) -> bool:
    """Ask a running pipeline to stop.

    Returns True when processing for this file is registered in *this* worker;
    a False result does not mean nothing is running — the pipeline may live in
    another process and will then pick the request up via the database.
    """
    event = _cancel_events.get(file_id)
    if event is None:
        return False
    event.set()
    return True


def is_cancellation_requested(file_id: str) -> bool:
    event = _cancel_events.get(file_id)
    return event is not None and event.is_set()


async def is_cancelled(file_id: str) -> bool:
    """Check both the in-process registry and the database."""
    if is_cancellation_requested(file_id):
        return True

    try:
        async with get_async_db_context() as db:
            file = await Files.get_file_by_id(file_id, db=db)
    except Exception as e:
        # A failing check must not abort a healthy job.
        log.debug('Cancellation check for %s failed: %s', file_id, e)
        return False

    if file is None:
        # The record was deleted while we were processing it.
        return True
    return (file.data or {}).get('status') == 'cancelled'


async def raise_if_cancelled(file_id: str) -> None:
    if await is_cancelled(file_id):
        raise FileProcessingCancelled(file_id)


def _abandon(task: 'asyncio.Future') -> None:
    """Drop a task we are no longer interested in, without a noisy traceback."""
    task.cancel()

    def _swallow(finished: 'asyncio.Future') -> None:
        if not finished.cancelled():
            finished.exception()

    task.add_done_callback(_swallow)


async def run_cancellable(awaitable: Awaitable[T], file_id: str) -> T:
    """Await `awaitable`, giving up as soon as the file's deletion is requested.

    Raises FileProcessingCancelled instead of returning in that case.  The
    abandoned work keeps running if it sits in a worker thread — threads cannot
    be interrupted — but its result is never used.

    Only wrap work whose result is held in memory (content extraction).  Work
    that writes to the vector database must be awaited normally, otherwise its
    write can land after the caller has already cleaned up.
    """
    work = asyncio.ensure_future(awaitable)
    ticks = 0

    while True:
        done, _ = await asyncio.wait({work}, timeout=POLL_INTERVAL)
        if work in done:
            return work.result()

        ticks += 1
        cancelled = is_cancellation_requested(file_id)
        if not cancelled and ticks % DB_POLL_EVERY == 0:
            cancelled = await is_cancelled(file_id)

        if cancelled:
            log.info('Abandoning in-flight processing of file %s on user request', file_id)
            _abandon(work)
            raise FileProcessingCancelled(file_id)
