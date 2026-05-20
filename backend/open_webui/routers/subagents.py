"""Admin config endpoints for the subagents feature.

Mirrors the shape of ``routers/retrieval.py``'s ``/config`` GET/POST pair so the
admin UI can read and write the four PersistentConfig values that drive
subagents: the feature flag, the default subagent model, the subagent system
prompt (prepended to the subagent's own model system prompt), and the parent
prompt (appended to the parent chat's system prompt when subagents are on).

Fields use the exact ``UPPER_SNAKE`` keys the frontend admin page binds to —
keeping the contract symmetric with the way ``WebSearch.svelte`` reads
``res.web.WEB_SEARCH_SYSTEM_PROMPT`` etc.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class SubagentConfigForm(BaseModel):
    # All optional so the admin UI can PATCH-style update only fields it cares
    # about without overwriting the others.
    ENABLE_SUBAGENTS: Optional[bool] = None
    SUBAGENT_DEFAULT_MODEL: Optional[str] = None
    SUBAGENT_SYSTEM_PROMPT: Optional[str] = None
    SUBAGENT_PARENT_PROMPT: Optional[str] = None


def _serialize(request: Request) -> dict:
    config = request.app.state.config
    return {
        "status": True,
        "ENABLE_SUBAGENTS": config.ENABLE_SUBAGENTS,
        "SUBAGENT_DEFAULT_MODEL": config.SUBAGENT_DEFAULT_MODEL,
        "SUBAGENT_SYSTEM_PROMPT": config.SUBAGENT_SYSTEM_PROMPT,
        "SUBAGENT_PARENT_PROMPT": config.SUBAGENT_PARENT_PROMPT,
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
    if form_data.SUBAGENT_PARENT_PROMPT is not None:
        config.SUBAGENT_PARENT_PROMPT = form_data.SUBAGENT_PARENT_PROMPT
    return _serialize(request)
