"""SDP negotiation for OpenAI Realtime WebRTC sessions.

Extracted from ``routers/audio.py`` to minimise the diff on that stock file.
The thin wrapper in ``audio.py`` handles FastAPI routing, auth, and rate
limiting; this module owns the negotiation logic itself.
"""

import asyncio
import logging
from typing import Any

import aiohttp

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT

log = logging.getLogger(__name__)


def _locale_to_iso639(locale: str) -> str:
    """Convert OWUI locale (e.g. 'en-US') to ISO-639-1 (e.g. 'en')."""
    if not locale:
        return ""
    lang = locale.split("-")[0].lower()
    return lang if len(lang) == 2 else ""


async def execute_negotiate(
    *,
    request: Any,
    form_data: Any,
    user: Any,
) -> dict:
    """Run the full SDP negotiate flow.

    Resolves system prompt, tools, and language; mints an ephemeral key with
    all config baked in; performs the SDP exchange with OpenAI; and stores
    the ephemeral key for the sideband worker.

    Returns ``{"sdp_answer": str, "call_id": str}``.
    """
    from fastapi import HTTPException, status

    api_key = request.app.state.config.AUDIO_RT_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Realtime API key is not configured.",
        )

    base_url = request.app.state.config.AUDIO_RT_API_BASE_URL
    model = form_data.model

    from open_webui.realtime.catalog import (
        get_effective_provider_model_id,
        model_uses_realtime,
    )
    from open_webui.utils.models import check_model_access
    from open_webui.env import BYPASS_MODEL_ACCESS_CONTROL
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL

    models = request.app.state.MODELS
    if model not in models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is not a registered model.",
        )

    if not BYPASS_MODEL_ACCESS_CONTROL and (
        user.role != "admin" or not BYPASS_ADMIN_ACCESS_CONTROL
    ):
        try:
            check_model_access(user, models[model])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            ) from e

    model_obj = models[model]
    if not model_uses_realtime(request, model_obj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model does not have realtime capability.",
        )
    provider_model_id = get_effective_provider_model_id(model_obj) or model

    from open_webui.socket.main import SESSION_POOL

    socket_session = SESSION_POOL.get(form_data.session_id)
    if not socket_session or socket_session.get("id") != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Realtime socket session is invalid or expired.",
        )
    chat_id = form_data.chat_id or ""

    from open_webui.realtime.bootstrap import (
        apply_user_realtime_settings,
        build_session_config,
        mint_realtime_client_secret,
    )
    from open_webui.realtime.ephemeral_store import store_ephemeral_key

    config = build_session_config(request.app.state.config)
    config.model = provider_model_id
    apply_user_realtime_settings(config, user)

    # --- 1. Resolve system prompt (same layering as normal chat) ---
    from open_webui.realtime.model_settings import get_realtime_model_system_prompt
    from open_webui.utils.payload import apply_system_prompt_to_body
    from open_webui.utils.misc import get_system_message
    from open_webui.models.folders import Folders
    from open_webui.models.chats import Chats
    from open_webui.utils.access_control import has_permission

    model_system = get_realtime_model_system_prompt(model)

    metadata_vars = {"variables": {}}
    form = {"messages": []}

    if form_data.system_prompt:
        if has_permission(
            user.id, "chat.system_prompt", request.app.state.config.USER_PERMISSIONS
        ):
            form["messages"] = [{"role": "system", "content": form_data.system_prompt}]
            form = apply_system_prompt_to_body(
                form_data.system_prompt, form, metadata_vars, user, replace=True
            )
        else:
            log.warning(
                "Ignoring realtime system prompt override without permission "
                "user=%s chat=%s model=%s",
                user.id, chat_id or "<none>", model,
            )

    if chat_id and not chat_id.startswith("local:"):
        folder_id = Chats.get_chat_folder_id(chat_id, user.id)
        if folder_id:
            folder = Folders.get_folder_by_id_and_user_id(folder_id, user.id)
            if folder and folder.data and "system_prompt" in folder.data:
                form = apply_system_prompt_to_body(
                    folder.data["system_prompt"], form, metadata_vars, user
                )

    if model_system:
        form = apply_system_prompt_to_body(
            model_system, form, metadata_vars, user
        )

    final_system = get_system_message(form.get("messages", []))
    config.system_instructions = (
        final_system.get("content", "") if final_system else ""
    )

    # --- 2. Resolve tools via process_chat_payload (always native FC) ---
    try:
        from open_webui.realtime.tool_specs import resolve_realtime_tool_specs

        config.tool_specs = await resolve_realtime_tool_specs(
            request,
            user=user,
            model_id=model,
            model_obj=model_obj,
            chat_id=chat_id,
            tool_ids=form_data.tool_ids,
            tool_servers=form_data.tool_servers,
            terminal_id=form_data.terminal_id,
            features=form_data.features,
        )
    except Exception:
        log.exception("Tool resolution failed in negotiate")
        if form_data.tool_ids or form_data.tool_servers or form_data.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Open WebUI: Realtime tool resolution failed.",
            )

    # --- 3. Set transcription language from user's UI locale ---
    config.transcription_language = _locale_to_iso639(form_data.language or "")

    # --- 4. Mint ephemeral key (all config baked in) ---
    from open_webui.realtime.contracts import build_realtime_bootstrap_binding

    r = None
    try:
        mint_result = await mint_realtime_client_secret(
            api_key, base_url, config, provider_model_id, ttl_seconds=7200,
        )
        eph_key = mint_result["value"]
        if not eph_key:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to mint ephemeral key — empty value from OpenAI.",
            )

        # --- 5. SDP exchange with OpenAI using ephemeral key ---
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                "Authorization": f"Bearer {eph_key}",
                "Content-Type": "application/sdp",
            }

            for sdp_attempt in range(2):
                r = await session.post(
                    url=f"{base_url}/realtime/calls",
                    data=form_data.sdp_offer,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                )
                if r.status < 500 or sdp_attempt == 1:
                    break
                log.warning("SDP exchange returned %d, retrying once...", r.status)
                await asyncio.sleep(0.5)

            if r.status >= 400:
                error_body = await r.text()
                error_preview = (
                    f"{error_body[:500]}..." if len(error_body) > 500 else error_body
                )
                log.error("SDP exchange failed: %d %s", r.status, error_preview)
                r.raise_for_status()
            sdp_answer = await r.text()

            call_id = ""
            location = r.headers.get("Location", "")
            if location:
                call_id = location.split("/").pop()

        # --- 6. Store ephemeral key + tool params for sideband ---
        if call_id:
            bootstrap_binding = build_realtime_bootstrap_binding(
                user_id=user.id,
                sid=form_data.session_id,
                chat_id=chat_id,
                model_id=model,
                tool_ids=form_data.tool_ids,
                tool_servers=form_data.tool_servers,
                features=form_data.features,
                terminal_id=form_data.terminal_id,
            )
            await store_ephemeral_key(
                call_id,
                eph_key,
                {
                    **bootstrap_binding,
                    "expires_at": mint_result.get("secret_expires_at")
                    or mint_result.get("token_expires_at"),
                    "session_token": getattr(
                        getattr(request.state, "token", None), "credentials", ""
                    ),
                    "oauth_session_id": request.cookies.get(
                        "oauth_session_id", ""
                    ),
                },
            )
        return {
            "sdp_answer": sdp_answer,
            "call_id": call_id,
        }
    except HTTPException:
        raise
    except Exception:
        log.exception("Realtime negotiate failed for model '%s'", model)
        detail = "Open WebUI: Realtime negotiation failed."
        status_code_val = 502

        if r is not None:
            try:
                res = await r.json()
                if "error" in res:
                    log.error("Upstream error detail: %s", res["error"])
            except Exception:
                pass

        raise HTTPException(
            status_code=status_code_val,
            detail=detail,
        )
