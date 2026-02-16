import re
import time
from urllib.parse import urlencode, parse_qs, urlparse

from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette_compress import CompressMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from starsessions import (
    SessionMiddleware as StarSessionsMiddleware,
    SessionAutoloadMiddleware,
)
from starsessions.stores.redis import RedisStore

from open_webui.config import CORS_ALLOW_ORIGIN
from open_webui.env import (
    ENABLE_COMPRESSION_MIDDLEWARE,
    ENABLE_STAR_SESSIONS_MIDDLEWARE,
    REDIS_URL,
    REDIS_KEY_PREFIX,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
)
from open_webui.internal.db import ScopedSession
from open_webui.utils.auth import get_http_authorization_cred
from open_webui.utils.security_headers import SecurityHeadersMiddleware

from open_webui.utils import logger


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "GET":
            path = request.url.path
            query_params = dict(parse_qs(urlparse(str(request.url)).query))

            redirect_params = {}

            if path.endswith("/watch") and "v" in query_params:
                youtube_video_id = query_params["v"][0]
                redirect_params["youtube"] = youtube_video_id

            if "shared" in query_params and len(query_params["shared"]) > 0:
                text = query_params["shared"][0]
                if text:
                    urls = re.match(r"https://\S+", text)
                    if urls:
                        from open_webui.retrieval.loaders.youtube import _parse_video_id

                        if youtube_video_id := _parse_video_id(urls[0]):
                            redirect_params["youtube"] = youtube_video_id
                        else:
                            redirect_params["load-url"] = urls[0]
                    else:
                        redirect_params["q"] = text

            if redirect_params:
                redirect_url = f"/?{urlencode(redirect_params)}"
                return RedirectResponse(url=redirect_url)

        response = await call_next(request)
        return response


class APIKeyRestrictionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header:
            parts = auth_header.split(" ", 1)
            if len(parts) == 2:
                token = parts[1]

        if token and token.startswith("sk-"):
            if request.app.state.config.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS:
                allowed_paths = [
                    path.strip()
                    for path in str(
                        request.app.state.config.API_KEYS_ALLOWED_ENDPOINTS
                    ).split(",")
                    if path.strip()
                ]

                request_path = request.url.path

                is_allowed = any(
                    request_path == allowed or request_path.startswith(allowed + "/")
                    for allowed in allowed_paths
                )

                if not is_allowed:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": "API key not allowed to access this endpoint."
                        },
                    )

        response = await call_next(request)
        return response


def register_http_middlewares(app: FastAPI) -> None:
    """Register HTTP middleware stack in the canonical order."""
    if ENABLE_COMPRESSION_MIDDLEWARE:
        app.add_middleware(CompressMiddleware)

    app.add_middleware(RedirectMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(APIKeyRestrictionMiddleware)

    @app.middleware("http")
    async def commit_session_after_request(request, call_next):
        response = await call_next(request)
        try:
            ScopedSession.commit()
        finally:
            ScopedSession.remove()
        return response

    @app.middleware("http")
    async def check_url(request, call_next):
        start_time = int(time.time())
        request.state.token = get_http_authorization_cred(
            request.headers.get("Authorization")
        )
        if request.state.token is None and request.cookies.get("token"):
            from fastapi.security import HTTPAuthorizationCredentials

            request.state.token = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=request.cookies.get("token")
            )

        request.state.enable_api_keys = app.state.config.ENABLE_API_KEYS
        response = await call_next(request)
        process_time = int(time.time()) - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.middleware("http")
    async def inspect_websocket(request, call_next):
        if (
            "/ws/socket.io" in request.url.path
            and request.query_params.get("transport") == "websocket"
        ):
            upgrade = (request.headers.get("Upgrade") or "").lower()
            connection = (request.headers.get("Connection") or "").lower().split(",")
            if upgrade != "websocket" or "upgrade" not in connection:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid WebSocket upgrade request"},
                )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGIN,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_session_middlewares(app: FastAPI) -> None:
    """Register session middleware stack with Redis-backed sessions fallback."""
    try:
        if ENABLE_STAR_SESSIONS_MIDDLEWARE:
            redis_session_store = RedisStore(
                url=REDIS_URL,
                prefix=(
                    f"{REDIS_KEY_PREFIX}:session:"
                    if REDIS_KEY_PREFIX
                    else "session:"
                ),
            )

            app.add_middleware(SessionAutoloadMiddleware)
            app.add_middleware(
                StarSessionsMiddleware,
                store=redis_session_store,
                cookie_name="owui-session",
                cookie_same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
                cookie_https_only=WEBUI_SESSION_COOKIE_SECURE,
            )
            logger.info("Using Redis for session")
        else:
            raise ValueError("No Redis URL provided")
    except Exception:
        app.add_middleware(
            SessionMiddleware,
            secret_key=WEBUI_SECRET_KEY,
            session_cookie="owui-session",
            same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
            https_only=WEBUI_SESSION_COOKIE_SECURE,
        )
