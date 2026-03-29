"""Realtime startup hooks owned by the realtime subsystem."""


import asyncio
import logging

from fastapi import FastAPI

from open_webui.env import WEBSOCKET_MANAGER
from open_webui.realtime.session_service import orphan_sweep_loop, session_manager
from open_webui.socket.main import sio

log = logging.getLogger(__name__)


async def _pending_text_listener() -> None:
    """Multi-worker pub/sub listener for pending text notifications.
    """
    from open_webui.realtime.pending_store import (
        _NOTIFY_CHANNEL,
        _redis_client,
        drain_pending_texts,
    )

    if _redis_client is None:
        return

    pubsub = _redis_client.pubsub()
    await pubsub.subscribe(_NOTIFY_CHANNEL)
    log.info("Pending text listener: subscribed to %s", _NOTIFY_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                session_id = (
                    message['data'].decode()
                    if isinstance(message['data'], bytes)
                    else message['data']
                )
                session = session_manager.get_session(session_id)
                if (
                    not session
                    or not session.is_ready
                    or session.assistant_responding
                    or session.tool_executing
                    or not session.ws
                ):
                    continue
                pending = await drain_pending_texts(session_id)
                if pending:
                    from open_webui.realtime.sideband import _flush_pending_to_ws
                    await _flush_pending_to_ws(
                        session, pending, "notified_pending", sio=sio
                    )
            except Exception:
                log.exception("Error handling pending text notification")
    except asyncio.CancelledError:
        pass
    finally:
        try:
            await pubsub.unsubscribe(_NOTIFY_CHANNEL)
        except Exception:
            pass


def start_realtime_background_tasks(app: FastAPI) -> list[asyncio.Task]:
    tasks = [asyncio.create_task(orphan_sweep_loop(sio, app.state.config))]
    if WEBSOCKET_MANAGER == 'redis':
        tasks.append(asyncio.create_task(_pending_text_listener()))
    app.state.realtime_tasks = tasks
    return tasks
