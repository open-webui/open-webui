"""Admin config endpoints for the client-side flex auto-flip feature.

The actual auto-flip logic lives in `src/lib/components/chat/Chat.svelte` and
reads its policy from `$config.features.flex_auto_flip_*` (surfaced in
`main.py`'s `/api/config` payload). These endpoints give admins a place to
read and update those values without restarting the server.

Mirrors the shape of `routers/subagents.py`'s `/config` GET/POST pair.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class FlexAutoFlipConfigForm(BaseModel):
    # All optional so the admin UI can PATCH-style update only fields it cares
    # about without overwriting the others.
    FLEX_AUTO_FLIP_ENABLED: Optional[bool] = None
    FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR: Optional[int] = None
    FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR: Optional[int] = None
    FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE: Optional[str] = None
    FLEX_AUTO_FLIP_THRESHOLD_RATIO: Optional[float] = None


def _serialize(request: Request) -> dict:
    config = request.app.state.config
    return {
        "status": True,
        "FLEX_AUTO_FLIP_ENABLED": config.FLEX_AUTO_FLIP_ENABLED,
        "FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR": config.FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR,
        "FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR": config.FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR,
        "FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE": config.FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE,
        "FLEX_AUTO_FLIP_THRESHOLD_RATIO": config.FLEX_AUTO_FLIP_THRESHOLD_RATIO,
    }


@router.get("/config")
async def get_flex_auto_flip_config(request: Request, user=Depends(get_admin_user)):
    return _serialize(request)


@router.post("/config/update")
async def update_flex_auto_flip_config(
    request: Request,
    form_data: FlexAutoFlipConfigForm,
    user=Depends(get_admin_user),
):
    config = request.app.state.config

    if form_data.FLEX_AUTO_FLIP_ENABLED is not None:
        config.FLEX_AUTO_FLIP_ENABLED = form_data.FLEX_AUTO_FLIP_ENABLED

    if form_data.FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR is not None:
        h = form_data.FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR
        if not (0 <= h <= 23):
            raise HTTPException(status_code=400, detail="start hour must be 0..23")
        config.FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR = h

    if form_data.FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR is not None:
        h = form_data.FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR
        if not (0 <= h <= 23):
            raise HTTPException(status_code=400, detail="end hour must be 0..23")
        config.FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR = h

    if form_data.FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE is not None:
        tz = form_data.FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE.strip()
        if not tz:
            raise HTTPException(status_code=400, detail="timezone cannot be empty")
        # Validate against zoneinfo so we reject typos at write time instead of
        # silently breaking the frontend's `Intl.DateTimeFormat` call.
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(tz)
        except Exception:
            raise HTTPException(
                status_code=400, detail=f"unknown IANA timezone: {tz}"
            )
        config.FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE = tz

    if form_data.FLEX_AUTO_FLIP_THRESHOLD_RATIO is not None:
        r = form_data.FLEX_AUTO_FLIP_THRESHOLD_RATIO
        if not (0.0 < r <= 1.0):
            raise HTTPException(
                status_code=400, detail="threshold_ratio must be in (0, 1]"
            )
        config.FLEX_AUTO_FLIP_THRESHOLD_RATIO = r

    return _serialize(request)
