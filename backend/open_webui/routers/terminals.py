"""Reverse proxy for admin-configured terminal servers.

Routes:
  GET  /                                   — list terminals the user has access to
  *    /{server_id}/{path:path}            — proxy request to terminal server

  Admin API (policy CRUD, instance management, server info):
  GET    /{server_id}/api/v1/policies          — list policies
  POST   /{server_id}/api/v1/policies          — create policy
  GET    /{server_id}/api/v1/policies/{pid}    — get policy
  PUT    /{server_id}/api/v1/policies/{pid}    — upsert policy
  DELETE /{server_id}/api/v1/policies/{pid}    — delete policy
  GET    /{server_id}/api/v1/instances         — list terminal instances
  DELETE /{server_id}/api/v1/instances/{iid}   — teardown instance
  GET    /{server_id}/api/v1/info              — server info
"""

import json as _json
import logging
import posixpath
from urllib.parse import unquote

import aiohttp
from fastapi import APIRouter, Depends, Request, Response, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_connection_access
from open_webui.models.groups import Groups
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()

STREAMING_CONTENT_TYPES = ('application/octet-stream', 'image/', 'application/pdf')
STRIPPED_RESPONSE_HEADERS = frozenset(('transfer-encoding', 'connection', 'content-encoding', 'content-length'))


def _sanitize_proxy_path(path: str) -> str | None:
    """Sanitize a proxy path to prevent directory traversal / SSRF.

    Returns the cleaned path, or None if the path is invalid.
    """
    decoded = unquote(path)
    normalized = posixpath.normpath(decoded)
    # Remove any leading slashes that would reset the base
    cleaned = normalized.lstrip('/')
    # Reject if normpath resolved to parent traversal or current-dir only
    if cleaned.startswith('..') or cleaned == '.':
        return None
    return cleaned


@router.get('/')
async def list_terminal_servers(request: Request, user=Depends(get_verified_user)):
    """Return terminal servers the authenticated user has access to."""
    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}

    return [
        {
            'id': connection.get('id', ''),
            'url': connection.get('url', ''),
            'name': connection.get('name', ''),
        }
        for connection in connections
        if connection.get('enabled', True) and has_connection_access(user, connection, user_group_ids)
    ]


# ---------------------------------------------------------------------------
# Admin API helpers
# ---------------------------------------------------------------------------


def _resolve_admin_connection(request: Request, server_id: str) -> dict | None:
    """Look up a terminal server connection by ID."""
    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    return next((c for c in connections if c.get('id') == server_id), None)


def _build_admin_headers(connection: dict) -> dict[str, str]:
    """Build authentication headers for proxying to a terminal server."""
    headers: dict[str, str] = {'Content-Type': 'application/json'}
    auth_type = connection.get('auth_type', 'bearer')
    if auth_type == 'bearer':
        key = connection.get('key', '')
        if key:
            headers['Authorization'] = f'Bearer {key}'
    return headers


async def _admin_proxy_json(
    connection: dict,
    method: str,
    path: str,
    body: dict | None = None,
) -> Response:
    """Proxy a JSON request to a terminal server's API and return the response."""
    base_url = (connection.get('url') or '').rstrip('/')
    if not base_url:
        return JSONResponse({'error': 'Terminal server URL not configured'}, status_code=503)

    url = f'{base_url}/{path}'
    headers = _build_admin_headers(connection)

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=30, connect=10),
    ) as session:
        try:
            kwargs: dict = {'headers': headers}
            if body is not None:
                kwargs['data'] = _json.dumps(body)

            async with session.request(method, url, **kwargs) as resp:
                response_body = await resp.read()
                filtered_headers = {
                    key: value
                    for key, value in resp.headers.items()
                    if key.lower() not in STRIPPED_RESPONSE_HEADERS
                }
                return Response(
                    content=response_body,
                    status_code=resp.status,
                    headers=filtered_headers,
                )
        except Exception as e:
            log.exception('Admin proxy error: %s', e)
            return JSONResponse({'error': f'Terminal server unreachable: {e}'}, status_code=502)


# ---------------------------------------------------------------------------
# Policy CRUD proxy
# ---------------------------------------------------------------------------


@router.get('/{server_id}/api/v1/policies')
async def list_policies(server_id: str, request: Request, user=Depends(get_admin_user)):
    """List all policies on a terminal orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    return await _admin_proxy_json(connection, 'GET', 'api/v1/policies')


@router.post('/{server_id}/api/v1/policies')
async def create_policy(server_id: str, request: Request, user=Depends(get_admin_user)):
    """Create a new policy on a terminal orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    body = await request.json()
    return await _admin_proxy_json(connection, 'POST', 'api/v1/policies', body)


@router.get('/{server_id}/api/v1/policies/{policy_id}')
async def get_policy(server_id: str, policy_id: str, request: Request, user=Depends(get_admin_user)):
    """Get a single policy from a terminal orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    return await _admin_proxy_json(connection, 'GET', f'api/v1/policies/{policy_id}')


@router.put('/{server_id}/api/v1/policies/{policy_id}')
async def upsert_policy(server_id: str, policy_id: str, request: Request, user=Depends(get_admin_user)):
    """Create or update a policy on a terminal orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    body = await request.json()
    return await _admin_proxy_json(connection, 'PUT', f'api/v1/policies/{policy_id}', body)


@router.delete('/{server_id}/api/v1/policies/{policy_id}')
async def delete_policy(server_id: str, policy_id: str, request: Request, user=Depends(get_admin_user)):
    """Delete a policy from a terminal orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    return await _admin_proxy_json(connection, 'DELETE', f'api/v1/policies/{policy_id}')


# ---------------------------------------------------------------------------
# Instance management proxy
# ---------------------------------------------------------------------------


@router.get('/{server_id}/api/v1/instances')
async def list_instances(server_id: str, request: Request, user=Depends(get_admin_user)):
    """List all active terminal instances on an orchestrator.

    Enriches each instance with ``user_name`` resolved from the Open WebUI
    users table so the admin UI can show human-readable names.
    """
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)

    resp = await _admin_proxy_json(connection, 'GET', 'api/v1/instances')

    # Enrich with user names when we successfully got a JSON list back.
    if resp.status_code == 200:
        try:
            instances = _json.loads(resp.body)
            if isinstance(instances, list):
                user_ids = {inst.get('user_id') for inst in instances if inst.get('user_id')}
                user_map = {}
                for uid in user_ids:
                    u = Users.get_user_by_id(uid)
                    if u:
                        user_map[uid] = u.name
                for inst in instances:
                    uid = inst.get('user_id', '')
                    inst['user_name'] = user_map.get(uid, '')
                return JSONResponse(instances)
        except Exception:
            pass  # Return the original response on any parse error

    return resp


@router.delete('/{server_id}/api/v1/instances/{instance_id}')
async def teardown_instance(
    server_id: str, instance_id: str, request: Request, user=Depends(get_admin_user),
):
    """Force-teardown a terminal instance on an orchestrator."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    return await _admin_proxy_json(connection, 'DELETE', f'api/v1/instances/{instance_id}')


# ---------------------------------------------------------------------------
# Server info proxy
# ---------------------------------------------------------------------------


@router.get('/{server_id}/api/v1/info')
async def get_server_info(server_id: str, request: Request, user=Depends(get_admin_user)):
    """Get info about a terminal server (backend type, resource caps, etc.)."""
    connection = _resolve_admin_connection(request, server_id)
    if connection is None:
        return JSONResponse({'error': 'Terminal server not found'}, status_code=404)
    return await _admin_proxy_json(connection, 'GET', 'api/v1/info')


# ---------------------------------------------------------------------------
# Catch-all proxy
# ---------------------------------------------------------------------------

PROXY_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']


@router.api_route('/{server_id}/{path:path}', methods=PROXY_METHODS)
async def proxy_terminal(
    server_id: str,
    path: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Proxy a request to the admin terminal server identified by *server_id*."""
    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        return JSONResponse({'error': f"Terminal server '{server_id}' not found"}, status_code=404)

    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    if not has_connection_access(user, connection, user_group_ids):
        return JSONResponse({'error': 'Access denied'}, status_code=403)

    base_url = (connection.get('url') or '').rstrip('/')
    if not base_url:
        return JSONResponse({'error': 'Terminal server URL not configured'}, status_code=503)

    safe_path = _sanitize_proxy_path(path)
    if safe_path is None:
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    target_url = f'{base_url}/{safe_path}'

    # Route through orchestrator policy endpoint if policy_id is set
    policy_id = connection.get('policy_id')
    if policy_id:
        target_url = f'{base_url}/p/{policy_id}/{safe_path}'

    if request.query_params:
        target_url += f'?{request.query_params}'

    headers = {'X-User-Id': user.id}
    cookies = {}
    auth_type = connection.get('auth_type', 'bearer')

    if auth_type == 'bearer':
        headers['Authorization'] = f'Bearer {connection.get("key", "")}'
    elif auth_type == 'session':
        cookies = request.cookies
        headers['Authorization'] = f'Bearer {request.state.token.credentials}'
    elif auth_type == 'system_oauth':
        cookies = request.cookies
        oauth_token = request.headers.get('x-oauth-access-token', '')
        if oauth_token:
            headers['Authorization'] = f'Bearer {oauth_token}'
    # auth_type == "none": no Authorization header

    content_type = request.headers.get('content-type')
    if content_type:
        headers['Content-Type'] = content_type

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

        upstream_content_type = upstream_response.headers.get('content-type', '')
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
        log.exception('Terminal proxy error: %s', error)
        return JSONResponse({'error': f'Terminal proxy error: {error}'}, status_code=502)


# ---------------------------------------------------------------------------
# WebSocket proxy for interactive terminal sessions
# ---------------------------------------------------------------------------


async def _resolve_authenticated_connection(ws: WebSocket, server_id: str):
    """Authenticate a WebSocket via first-message auth and resolve the terminal server.

    The client must send ``{"type": "auth", "token": "<jwt>"}`` as its first
    message after connecting.

    Returns ``(user, connection)`` on success, or ``None`` after closing *ws*
    with an appropriate error code.
    """
    import asyncio
    import json
    from open_webui.utils.auth import decode_token

    # First-message authentication
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        payload = json.loads(raw)
        if payload.get('type') != 'auth':
            await ws.close(code=4001, reason='Expected auth message')
            return None
        token = payload.get('token', '')
        data = decode_token(token)
        if data is None or 'id' not in data:
            await ws.close(code=4001, reason='Invalid token')
            return None
        user = Users.get_user_by_id(data['id'])
        if user is None:
            await ws.close(code=4001, reason='User not found')
            return None
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await ws.close(code=4001, reason='Auth timeout or invalid payload')
        return None
    except Exception:
        await ws.close(code=4001, reason='Invalid token')
        return None

    # Resolve terminal server
    connections = ws.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        await ws.close(code=4004, reason='Terminal server not found')
        return None

    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    if not has_connection_access(user, connection, user_group_ids):
        await ws.close(code=4003, reason='Access denied')
        return None

    return user, connection


@router.websocket('/{server_id}/api/terminals/{session_id}')
async def ws_terminal(
    ws: WebSocket,
    server_id: str,
    session_id: str,
):
    """Proxy an interactive WebSocket terminal session to a terminal server.

    Uses first-message auth: the client sends ``{"type": "auth", "token": "<jwt>"}``
    as its first message. The proxy validates the JWT, then connects to the
    upstream terminal server and authenticates with the server's API key.
    """
    await ws.accept()

    result = await _resolve_authenticated_connection(ws, server_id)
    if result is None:
        return
    user, connection = result

    base_url = (connection.get('url') or '').rstrip('/')
    if not base_url:
        await ws.close(code=4003, reason='Terminal server URL not configured')
        return

    # Build upstream WebSocket URL (no token in URL)
    ws_base = base_url.replace('https://', 'wss://').replace('http://', 'ws://')

    # Route through orchestrator policy endpoint if policy_id is set
    policy_id = connection.get('policy_id')
    upstream_params = {}
    # For orchestrator-backed servers, pass user_id
    upstream_params['user_id'] = user.id

    import urllib.parse

    if policy_id:
        upstream_url = f'{ws_base}/p/{policy_id}/api/terminals/{session_id}'
    else:
        upstream_url = f'{ws_base}/api/terminals/{session_id}'
    if upstream_params:
        upstream_url += f'?{urllib.parse.urlencode(upstream_params)}'

    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(upstream_url) as upstream:
            import asyncio
            import json as _json

            # First-message auth to upstream terminal server
            auth_type = connection.get('auth_type', 'bearer')
            if auth_type == 'bearer':
                key = connection.get('key', '')
                await upstream.send_str(_json.dumps({'type': 'auth', 'token': key}))

            async def _client_to_upstream():
                """Forward client → upstream."""
                try:
                    while True:
                        msg = await ws.receive()
                        if msg['type'] == 'websocket.disconnect':
                            break
                        elif 'bytes' in msg and msg['bytes']:
                            await upstream.send_bytes(msg['bytes'])
                        elif 'text' in msg and msg['text']:
                            await upstream.send_str(msg['text'])
                except Exception:
                    pass

            async def _upstream_to_client():
                """Forward upstream → client."""
                try:
                    async for msg in upstream:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            await ws.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            await ws.send_text(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
                except Exception:
                    pass

            await asyncio.gather(
                _client_to_upstream(),
                _upstream_to_client(),
                return_exceptions=True,
            )
    except Exception as e:
        log.exception('Terminal WebSocket proxy error: %s', e)
    finally:
        await session.close()
        try:
            await ws.close()
        except Exception:
            pass
