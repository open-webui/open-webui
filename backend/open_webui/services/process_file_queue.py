from typing import Optional
import asyncio
import logging
from open_webui.models.users import Users
from open_webui.models.files import Files

from open_webui.services.files_service import process_uploaded_file

############################
# Sequential file-processing queue
############################
# Uploads only enqueue a lightweight job and return immediately, so a bulk
# upload of many files is accepted fast. A single worker (started in the app
# lifespan, see file_processing_worker_loop) drains this queue one file at a
# time — extract → process/embed — so the backend is never hit by a
# thundering herd of concurrent extraction/embedding/LLM calls.

_file_processing_queue: Optional[asyncio.Queue] = None
log = logging.getLogger(__name__)


def get_file_processing_queue() -> asyncio.Queue:
    """Return the process-wide processing queue, creating it lazily.

    Created lazily (rather than at import) so it binds to the running event
    loop that serves requests and the worker.
    """
    global _file_processing_queue
    if _file_processing_queue is None:
        _file_processing_queue = asyncio.Queue()
    return _file_processing_queue


async def enqueue_file_processing(job: dict) -> None:
    """Queue a file for sequential background processing."""
    await get_file_processing_queue().put(job)


async def _process_queued_file(app, job: dict) -> None:
    # Lazy import avoids a circular import at module load time.
    from open_webui.utils.automations import _build_request

    file_id = job.get('file_id')
    if not file_id:
        log.error(f"Skipping file processing job: missing file_id in {job}")
        return

    user = await Users.get_user_by_id(job['user_id'])
    if not user:
        log.warning(f"Skipping file {file_id}: user {job.get('user_id')} not found")
        return
    file_item = await Files.get_file_by_id(file_id)
    if not file_item:
        log.warning(f'Skipping file {file_id}: file record not found')
        return

    request = _build_request(app)
    await process_uploaded_file(
        request,
        job.get('content_type'),
        job.get('file_path'),
        file_item,
        job.get('file_metadata') or {},
        user,
    )


async def file_processing_worker_loop(app) -> None:
    """Drain the file-processing queue strictly one file at a time.

    Bulk uploads enqueue many jobs instantly, but this single worker processes
    them sequentially so concurrent uploads cannot overwhelm the extraction,
    embedding, or LLM backends.
    """
    queue = get_file_processing_queue()

    # Crash recovery: re-enqueue files left in 'pending' by a previous run.
    try:
        pending_files = await Files.get_pending_files()
        for file_item in pending_files:
            meta = file_item.meta or {}
            await queue.put(
                {
                    'file_id': file_item.id,
                    'user_id': file_item.user_id,
                    'content_type': meta.get('content_type'),
                    'file_path': file_item.path,
                    'file_metadata': (meta.get('data') or {}),
                }
            )
        if pending_files:
            log.info(f'Re-enqueued {len(pending_files)} pending file(s) after restart')
    except Exception:
        log.exception('File processing worker: failed to recover pending files')

    log.info('File processing worker started (sequential)')
    while True:
        job = await queue.get()
        try:
            await _process_queued_file(app, job)
        except Exception:
            log.exception(f"File processing worker error for file {job.get('file_id')}")
        finally:
            queue.task_done()
