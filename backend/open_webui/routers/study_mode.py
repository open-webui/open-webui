from fastapi import APIRouter, Depends, Request

import logging

from open_webui.utils.auth import get_verified_user

from open_webui.config import (
    DEFAULT_STUDY_MODE_PROMPT,
)

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


##################################
#
# Study Mode Endpoints
#
##################################


@router.get("/config")
async def get_study_mode_config(request: Request, user=Depends(get_verified_user)):
    return {
        "PROMPT": (
            request.app.state.config.STUDY_MODE_PROMPT
            if request.app.state.config.STUDY_MODE_PROMPT
            else DEFAULT_STUDY_MODE_PROMPT
        ),
        "ENABLE_STUDY_MODE": request.app.state.config.ENABLE_STUDY_MODE,
    }
