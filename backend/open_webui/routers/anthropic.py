import json
import logging
from typing import Optional

import aiohttp

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from open_webui.models.models import Models
from open_webui.models.access_grants import AccessGrants
from open_webui.routers.openai import get_all_models, get_headers_and_cookies
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.utils.auth import get_admin_user, get_current_user_by_api_key
from open_webui.utils.misc import cleanup_response, stream_wrapper

log = logging.getLogger(__name__)

router = APIRouter()


##########################################
#
# Auth dependency
#
##########################################


async def get_verified_user_by_api_key(request: Request):
    """
    Authenticate users via the x-api-key header using Open WebUI API keys.
    This matches Anthropic SDK client behavior where credentials are sent
    via the x-api-key header.
    """
    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")

    user = get_current_user_by_api_key(request, api_key)
    return user


##########################################
#
# Admin config endpoints
#
##########################################


class AnthropicConfigForm(BaseModel):
    ENABLE_ANTHROPIC_API: Optional[bool] = None


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
    }


@router.post("/config/update")
async def update_config(
    request: Request, form_data: AnthropicConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_ANTHROPIC_API = form_data.ENABLE_ANTHROPIC_API

    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
    }


##########################################
#
# Proxy endpoint
#
##########################################


@router.post("/v1/messages")
async def proxy_messages(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user_by_api_key),
):
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        raise HTTPException(status_code=503, detail="Anthropic API proxy is disabled")

    bypass_filter = BYPASS_MODEL_ACCESS_CONTROL

    payload = {**form_data}
    model_id = payload.get("model")

    if not model_id:
        raise HTTPException(status_code=400, detail="model is required")

    # Check model access control
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or AccessGrants.has_access(
                    user_id=user.id,
                    resource_type="model",
                    resource_id=model_info.id,
                    permission="read",
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    # Resolve the backend URL and API key from the existing OpenAI model registry.
    # The model is already configured as an OpenAI-compatible connection in the admin UI,
    # and vLLM serves both /v1/chat/completions and /v1/messages on the same server.
    models = request.app.state.OPENAI_MODELS
    if not models or model_id not in models:
        await get_all_models(request, user=user)
        models = request.app.state.OPENAI_MODELS
    model = models.get(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    idx = model["urlIdx"]
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    # Strip prefix_id from model name if configured
    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, user=user
    )

    request_url = f"{url}/messages"
    body = json.dumps(payload)

    r = None
    session = None
    streaming = False

    try:
        session = aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE (streaming)
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                stream_wrapper(r, session),
                status_code=r.status,
                headers=dict(r.headers),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            return response
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)
