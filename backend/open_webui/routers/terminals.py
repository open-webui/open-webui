"""Reverse proxy for admin-configured terminal servers.

Routes:
  GET  /                         — list terminals the user has access to
  *    /{server_id}/{path:path}  — proxy request to terminal server
"""

import logging

import aiohttp
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_connection_access
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

router = APIRouter()

STREAMING_CONTENT_TYPES = ("application/octet-stream", "image/", "application/pdf")
STRIPPED_RESPONSE_HEADERS = frozenset(
    ("transfer-encoding", "connection", "content-encoding", "content-length")
)


@router.get("/")
async def list_terminal_servers(request: Request, user=Depends(get_verified_user)):
    """Return terminal servers the authenticated user has access to."""
    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}

    return [
        {"id": connection.get("id", ""), "url": connection.get("url", ""), "name": connection.get("name", "")}
        for connection in connections
        if has_connection_access(user, connection, user_group_ids)
    ]


PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@router.api_route("/{server_id}/{path:path}", methods=PROXY_METHODS)
async def proxy_terminal(
    server_id: str,
    path: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Proxy a request to the admin terminal server identified by *server_id*."""
    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    connection = next((c for c in connections if c.get("id") == server_id), None)

    if connection is None:
        return JSONResponse({"error": f"Terminal server '{server_id}' not found"}, status_code=404)

    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    if not has_connection_access(user, connection, user_group_ids):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    base_url = (connection.get("url") or "").rstrip("/")
    if not base_url:
        return JSONResponse({"error": "Terminal server URL not configured"}, status_code=503)

    target_url = f"{base_url}/{path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    headers = {"X-User-Id": user.id}
    cookies = {}
    auth_type = connection.get("auth_type", "bearer")

    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {connection.get('key', '')}"
    elif auth_type == "session":
        cookies = request.cookies
        headers["Authorization"] = f"Bearer {request.state.token.credentials}"
    elif auth_type == "system_oauth":
        cookies = request.cookies
        oauth_token = request.headers.get("x-oauth-access-token", "")
        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"
    # auth_type == "none": no Authorization header

    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type

    body = await request.body()
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=300, connect=10),
        trust_env=True,
    )

    try:
        upstream_response = await session.request(
            method=request.method,
            url=target_url,
            headers=headers,
            cookies=cookies,
            data=body or None,
        )

        upstream_content_type = upstream_response.headers.get("content-type", "")
        filtered_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() not in STRIPPED_RESPONSE_HEADERS
        }

        # Stream binary responses directly
        if any(t in upstream_content_type for t in STREAMING_CONTENT_TYPES):
            async def cleanup():
                await upstream_response.release()
                await session.close()

            return StreamingResponse(
                content=upstream_response.content.iter_any(),
                status_code=upstream_response.status,
                headers=filtered_headers,
                background=BackgroundTask(cleanup),
            )

        # Buffer text/JSON responses
        response_body = await upstream_response.read()
        status_code = upstream_response.status
        await upstream_response.release()
        await session.close()

        return Response(content=response_body, status_code=status_code, headers=filtered_headers)

    except Exception as error:
        await session.close()
        log.exception("Terminal proxy error: %s", error)
        return JSONResponse({"error": f"Terminal proxy error: {error}"}, status_code=502)
