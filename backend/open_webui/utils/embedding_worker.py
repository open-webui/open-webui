"""Durable knowledge-base embedding worker.

Ingestion is split into two phases:

  1. Upload (fast)  — files are stored and a ``knowledge_file`` link row is
     created immediately with ``status='pending'``. No embedding happens on the
     request path, so the user never has to keep a session open.
  2. Embed (durable) — this worker drains pending links, embeds each file into
     its knowledge-base collection, and flips the link to ``completed`` (or
     ``failed`` + error).

Because the queue *is* the ``knowledge_file.status`` column in the database,
work survives a server restart: on startup the worker simply keeps draining
whatever is still ``pending``. The claim is atomic (UPDATE ... WHERE
status='pending'), so it is safe to run one of these per process even across
replicas.
"""

import asyncio
import logging
import os
import random
from types import SimpleNamespace

from open_webui.internal.db import get_async_db
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.users import Users
from open_webui.routers.retrieval import ProcessFileForm, process_file

log = logging.getLogger(__name__)

# How long to wait between polls when the queue is empty. Kept short because
# the loop already sleeps only when there is nothing to do.
EMBEDDING_WORKER_IDLE_INTERVAL = float(os.getenv('EMBEDDING_WORKER_IDLE_INTERVAL', '5'))


async def _embed_one(app, link) -> None:
    """Embed a single claimed link into its knowledge-base collection."""
    # process_file only ever reads ``request.app.state`` — a light shim avoids
    # constructing a full ASGI request.
    request = SimpleNamespace(app=app)

    user = await Users.get_user_by_id(link.user_id)
    if not user:
        await Knowledges.set_embedding_status(
            link.knowledge_id,
            link.file_id,
            'failed',
            error='Owner user not found',
        )
        return

    file = await Files.get_file_by_id(link.file_id)
    if not file:
        await Knowledges.set_embedding_status(
            link.knowledge_id,
            link.file_id,
            'failed',
            error='File not found',
        )
        return

    try:
        # process_file forwards `db` to its model calls, so it must receive a
        # real session (its default is a FastAPI Depends sentinel).
        async with get_async_db() as db:
            await process_file(
                request,
                ProcessFileForm(file_id=link.file_id, collection_name=link.knowledge_id),
                user=user,
                db=db,
            )
        await Knowledges.set_embedding_status(link.knowledge_id, link.file_id, 'completed')
    except Exception as e:
        log.warning(f'Embedding failed for file {link.file_id} in KB {link.knowledge_id}: {e}')
        detail = getattr(e, 'detail', None) or str(e)
        await Knowledges.set_embedding_status(
            link.knowledge_id, link.file_id, 'failed', error=str(detail)
        )


async def embedding_worker_loop(app) -> None:
    """Continuously drain pending knowledge-base embeddings."""
    log.info(f'Embedding worker started (idle interval: {EMBEDDING_WORKER_IDLE_INTERVAL}s)')

    # Recover links left 'processing' by a previous run that was killed
    # mid-embed — without this they would never be re-driven.
    try:
        recovered = await Knowledges.requeue_stale_processing_embeddings()
        if recovered:
            log.info(f'Re-queued {recovered} stale processing embedding(s) from a previous run')
    except Exception:
        log.exception('Embedding worker: failed to recover stale processing rows')

    while True:
        try:
            link = await Knowledges.claim_next_pending_embedding()
            if link is None:
                # Nothing to do (or lost a claim race) — back off briefly.
                await asyncio.sleep(EMBEDDING_WORKER_IDLE_INTERVAL + random.uniform(0, 1))
                continue

            await _embed_one(app, link)
            # Immediately loop to grab the next item without sleeping.
        except Exception:
            log.exception('Embedding worker error')
            await asyncio.sleep(EMBEDDING_WORKER_IDLE_INTERVAL)
