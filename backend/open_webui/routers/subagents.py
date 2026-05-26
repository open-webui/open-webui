"""Admin config + user-initiated rerun endpoints for the subagents feature.

The ``/config`` GET/POST pair mirrors the shape of
``routers/retrieval.py``'s admin-config endpoints. The ``/rerun`` POST is the
user-side hook for the "Redo this turn" / "Restart from beginning" buttons
inside a SubagentBlock in the parent chat UI — it spawns the rerun as a
background asyncio task and returns immediately; live progress streams back
to the user via the same ``chat:subagent:update`` socket events the original
launch used.
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.tasks import create_task
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class SubagentConfigForm(BaseModel):
    # All optional so the admin UI can PATCH-style update only fields it cares
    # about without overwriting the others.
    ENABLE_SUBAGENTS: Optional[bool] = None
    SUBAGENT_DEFAULT_MODEL: Optional[str] = None
    SUBAGENT_SYSTEM_PROMPT: Optional[str] = None
    SUBAGENT_SYSTEM_PROMPT_APPEND: Optional[str] = None
    SUBAGENT_PARENT_PROMPT: Optional[str] = None
    SUBAGENT_DEFAULT_REASONING_EFFORT: Optional[str] = None
    SUBAGENT_DEFAULT_SERVICE_TIER: Optional[str] = None


def _serialize(request: Request) -> dict:
    config = request.app.state.config
    return {
        "status": True,
        "ENABLE_SUBAGENTS": config.ENABLE_SUBAGENTS,
        "SUBAGENT_DEFAULT_MODEL": config.SUBAGENT_DEFAULT_MODEL,
        "SUBAGENT_SYSTEM_PROMPT": config.SUBAGENT_SYSTEM_PROMPT,
        "SUBAGENT_SYSTEM_PROMPT_APPEND": getattr(
            config, "SUBAGENT_SYSTEM_PROMPT_APPEND", ""
        ),
        "SUBAGENT_PARENT_PROMPT": config.SUBAGENT_PARENT_PROMPT,
        "SUBAGENT_DEFAULT_REASONING_EFFORT": config.SUBAGENT_DEFAULT_REASONING_EFFORT,
        "SUBAGENT_DEFAULT_SERVICE_TIER": config.SUBAGENT_DEFAULT_SERVICE_TIER,
    }


@router.get("/config")
async def get_subagents_config(request: Request, user=Depends(get_admin_user)):
    return _serialize(request)


@router.post("/config/update")
async def update_subagents_config(
    request: Request, form_data: SubagentConfigForm, user=Depends(get_admin_user)
):
    config = request.app.state.config
    if form_data.ENABLE_SUBAGENTS is not None:
        config.ENABLE_SUBAGENTS = form_data.ENABLE_SUBAGENTS
    if form_data.SUBAGENT_DEFAULT_MODEL is not None:
        config.SUBAGENT_DEFAULT_MODEL = form_data.SUBAGENT_DEFAULT_MODEL
    if form_data.SUBAGENT_SYSTEM_PROMPT is not None:
        config.SUBAGENT_SYSTEM_PROMPT = form_data.SUBAGENT_SYSTEM_PROMPT
    if form_data.SUBAGENT_SYSTEM_PROMPT_APPEND is not None:
        try:
            config.SUBAGENT_SYSTEM_PROMPT_APPEND = (
                form_data.SUBAGENT_SYSTEM_PROMPT_APPEND
            )
        except (AttributeError, KeyError):
            pass  # config key not registered yet — requires server restart
    if form_data.SUBAGENT_PARENT_PROMPT is not None:
        config.SUBAGENT_PARENT_PROMPT = form_data.SUBAGENT_PARENT_PROMPT
    if form_data.SUBAGENT_DEFAULT_REASONING_EFFORT is not None:
        config.SUBAGENT_DEFAULT_REASONING_EFFORT = (
            form_data.SUBAGENT_DEFAULT_REASONING_EFFORT
        )
    if form_data.SUBAGENT_DEFAULT_SERVICE_TIER is not None:
        config.SUBAGENT_DEFAULT_SERVICE_TIER = form_data.SUBAGENT_DEFAULT_SERVICE_TIER
    return _serialize(request)


class SubagentRerunForm(BaseModel):
    parent_chat_id: str
    parent_message_id: str
    # Caller's current socket session — used so the rerun's events route to
    # the user's open browser tab. The session_id is what
    # ``get_event_emitter`` uses to ``sio.emit(... to=session_id)``.
    session_id: str
    # Key into ``parent_message.subagent_runs`` for the block the user clicked
    # the redo button on.
    entry_key: str
    # ``"this_turn"``: re-run just the user→assistant pair this entry owns.
    # ``"from_launch"``: wipe the subagent chat and re-run from the original
    # launch's prompt + background.
    scope: Literal["this_turn", "from_launch"]


@router.post("/rerun")
async def rerun_subagent(
    request: Request,
    form_data: SubagentRerunForm,
    user=Depends(get_verified_user),
):
    """Spawn a subagent rerun as a background task and return immediately.

    Live progress comes back via ``chat:subagent:update`` socket events
    scoped to the parent chat — the same path the original launch uses, so
    the existing handler in ``Chat.svelte`` updates ``$subagentLiveStates``
    and the SubagentBlock re-renders in place.
    """
    from open_webui.utils.subagent import rerun_subagent_turn

    # Pre-validate access here (cheap + gives a synchronous 4xx) so we don't
    # silently swallow auth/lookup errors inside the background task.
    from open_webui.models.chats import Chats

    parent_chat = Chats.get_chat_by_id_and_user_id(
        form_data.parent_chat_id, user.id
    )
    if parent_chat is None:
        raise HTTPException(status_code=404, detail="Parent chat not found")

    async def _run():
        try:
            await rerun_subagent_turn(
                request=request,
                user=user,
                parent_chat_id=form_data.parent_chat_id,
                parent_message_id=form_data.parent_message_id,
                session_id=form_data.session_id,
                entry_key=form_data.entry_key,
                scope=form_data.scope,
            )
        except Exception as e:
            log.exception(f"subagent rerun task failed: {e}")

    task_id, _ = await create_task(
        request.app.state.redis,
        _run(),
        id=form_data.parent_chat_id,
    )
    return {"status": True, "task_id": task_id}
