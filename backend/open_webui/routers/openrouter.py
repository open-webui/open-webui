import logging
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from open_webui.config import OPENROUTER_API_BASE_URL, OPENROUTER_DEFAULT_MODEL_ID
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

router = APIRouter()


class OpenRouterConfigResponse(BaseModel):
    OPENROUTER_API_KEY_SET: bool
    OPENROUTER_ANONYMOUS_ENABLED: bool
    OPENROUTER_API_BASE_URL: str
    OPENROUTER_DEFAULT_MODEL_ID: str


class OpenRouterConfigUpdateForm(BaseModel):
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_ANONYMOUS_ENABLED: Optional[bool] = None


def _get_config_response(request: Request) -> dict:
    api_key = (request.app.state.config.OPENROUTER_API_KEY or "").strip()
    if not api_key:
        try:
            for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS or []):
                if "openrouter.ai" in str(url):
                    api_key = (
                        (request.app.state.config.OPENAI_API_KEYS[idx] or "").strip()
                        if idx < len(request.app.state.config.OPENAI_API_KEYS or [])
                        else ""
                    )
                    if api_key:
                        break
        except Exception:
            api_key = ""
    return {
        "OPENROUTER_API_KEY_SET": bool(api_key),
        "OPENROUTER_ANONYMOUS_ENABLED": bool(
            request.app.state.config.OPENROUTER_ANONYMOUS_ENABLED
        ),
        "OPENROUTER_API_BASE_URL": OPENROUTER_API_BASE_URL,
        "OPENROUTER_DEFAULT_MODEL_ID": OPENROUTER_DEFAULT_MODEL_ID,
    }


@router.get("/config", response_model=OpenRouterConfigResponse)
async def get_openrouter_config(request: Request, user=Depends(get_admin_user)):
    return _get_config_response(request)


@router.post("/config/update", response_model=OpenRouterConfigResponse)
async def update_openrouter_config(
    request: Request, form_data: OpenRouterConfigUpdateForm, user=Depends(get_admin_user)
):
    if form_data.OPENROUTER_API_KEY is not None:
        request.app.state.config.OPENROUTER_API_KEY = form_data.OPENROUTER_API_KEY.strip()

    if form_data.OPENROUTER_ANONYMOUS_ENABLED is not None:
        request.app.state.config.OPENROUTER_ANONYMOUS_ENABLED = bool(
            form_data.OPENROUTER_ANONYMOUS_ENABLED
        )

    return _get_config_response(request)
