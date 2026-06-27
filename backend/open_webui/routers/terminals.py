"""Reverse proxy for admin-configured terminal servers.

Routes:
  GET  /                         — list terminals the user has access to
  *    /{server_id}/{path:path}  — proxy request to terminal server
"""

import logging
import posixpath
import unicodedata
from urllib.parse import quote, unquote

import aiohttp
from fastapi import APIRouter, Depends, Query, Request, Response, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from open_webui.config import TERMINAL_PROXY_HEADERS
from open_webui.events import EVENTS, publish_event
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from open_webui.utils.access_control import has_connection_access
from open_webui.utils.auth import get_verified_user
from starlette.background import BackgroundTask

log = logging.getLogger(__name__)

router = APIRouter()

STREAMING_CONTENT_TYPES = ('application/octet-stream', 'image/', 'application/pdf')
STRIPPED_RESPONSE_HEADERS = frozenset(('transfer-encoding', 'connection', 'content-encoding', 'content-length'))


def _sanitize_proxy_path(path: str) -> str | None:
    """Sanitize a proxy path to prevent directory traversal / SSRF.

    Returns the cleaned path, or None if the path is invalid.
    Trailing slashes are preserved — many upstream frameworks treat
    ``/path`` and ``/path/`` differently.
    """
    # Decode until stable: a single unquote pass leaves %252e%252e as %2e%2e,
    # which the upstream then re-decodes into '..', bypassing the check below.
    decoded = path
    for _ in range(8):
        once = unquote(decoded)
        if once == decoded:
            break
        decoded = once
    # Fail closed: still encoded after the cap means the upstream would decode further into traversal.
    if unquote(decoded) != decoded:
        return None
    had_trailing_slash = decoded.endswith('/')
    normalized = posixpath.normpath(decoded)
    # Remove any leading slashes that would reset the base
    cleaned = normalized.lstrip('/')
    # Reject if normpath resolved to parent traversal or current-dir only
    if cleaned.startswith('..') or cleaned == '.':
        return None
    # Restore trailing slash if the original path had one
    if had_trailing_slash and cleaned and not cleaned.endswith('/'):
        cleaned += '/'
    return cleaned


@router.get('/')
async def list_terminal_servers(request: Request, user=Depends(get_verified_user)):
    """Return terminal servers the authenticated user has access to."""
    connections = await Config.get('terminal_server.connections', []) or []
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}

    return [
        {
            'id': connection.get('id', ''),
            'url': connection.get('url', ''),
            'name': connection.get('name', ''),
        }
        for connection in connections
        if connection.get('enabled', True) and await has_connection_access(user, connection, user_group_ids)
    ]


PROXY_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
INLINE_IMAGE_EXTENSIONS = frozenset(('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'avif'))


def _is_absolute_terminal_path(path: str) -> bool:
    normalized = path.replace('\\', '/')
    return normalized.startswith('/') or (
        len(normalized) >= 3 and normalized[1] == ':' and normalized[2] == '/' and normalized[0].isalpha()
    )


def _normalize_terminal_file_path(path: str) -> str | None:
    if not path or '\x00' in path:
        return None

    decoded = path
    for _ in range(8):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value

    normalized = decoded.replace('\\', '/')
    if not _is_absolute_terminal_path(normalized):
        return None

    if '..' in [part for part in normalized.split('/') if part]:
        return None

    if normalized.startswith('/'):
        return posixpath.normpath(normalized)

    drive = normalized[:2]
    rest = posixpath.normpath('/' + normalized[3:]).lstrip('/')
    return f'{drive}/{rest}' if rest else f'{drive}/'


def _is_inline_image_path(path: str) -> bool:
    extension = path.replace('\\', '/').rsplit('.', 1)[-1].lower()
    return extension in INLINE_IMAGE_EXTENSIONS


def _sanitize_download_filename(filename: str) -> str:
    sanitized = ''.join(char for char in filename if char.isprintable() and char not in {'"', '\\'})
    return sanitized[:255] or 'download'


def _ascii_filename_fallback(filename: str) -> str:
    fallback = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    sanitized = ''.join(char for char in fallback if 0x20 <= ord(char) < 0x7F and char not in {'"', '\\'})
    return sanitized[:255] or 'download'


@router.get('/{server_id}/files/content')
async def get_terminal_file_content(
    server_id: str,
    request: Request,
    path: str = Query(..., description='Terminal filesystem path to serve.'),
    download: bool = Query(False, description='If true, force browser download.'),
    user=Depends(get_verified_user),
):
    """Serve terminal files through Open WebUI without exposing upstream credentials."""
    terminal_path = _normalize_terminal_file_path(path)
    if terminal_path is None:
        return JSONResponse({'error': 'Only absolute sandbox file paths are supported'}, status_code=400)

    connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        return JSONResponse({'error': f"Terminal server '{server_id}' not found"}, status_code=404)

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
    if not await has_connection_access(user, connection, user_group_ids):
        return JSONResponse({'error': 'Access denied'}, status_code=403)

    base_url = (connection.get('url') or '').rstrip('/')
    if not base_url:
        return JSONResponse({'error': 'Terminal server URL not configured'}, status_code=503)

    policy_id = connection.get('policy_id')
    target_url = f'{base_url}/files/view'
    if policy_id:
        target_url = f'{base_url}/p/{policy_id}/files/view'

    headers = {'X-User-Id': user.id}
    for forwarded_header in ('range', 'if-range'):
        value = request.headers.get(forwarded_header)
        if value:
            headers[forwarded_header] = value

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

    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=300, connect=10),
        trust_env=True,
    )

    try:
        upstream_response = await session.get(
            target_url,
            params={'path': terminal_path},
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        filtered_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() not in STRIPPED_RESPONSE_HEADERS and key.lower() != 'content-disposition'
        }
        if TERMINAL_PROXY_HEADERS:
            filtered_headers.update(TERMINAL_PROXY_HEADERS)
        filtered_headers['Cache-Control'] = 'private, no-store'
        filtered_headers['X-Content-Type-Options'] = 'nosniff'

        if upstream_response.status >= 400:
            status_code = upstream_response.status
            upstream_response.release()
            await session.close()
            return JSONResponse(
                {'error': f'Terminal file request failed with status {status_code}'},
                status_code=status_code,
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Content-Type-Options': 'nosniff',
                },
            )

        filename = _sanitize_download_filename(
            terminal_path.replace('\\', '/').rstrip('/').split('/')[-1] or 'download'
        )
        content_type = upstream_response.headers.get('content-type', '').lower()
        can_inline = _is_inline_image_path(terminal_path) and content_type.startswith('image/')
        disposition = 'inline' if not download and can_inline else 'attachment'
        ascii_filename = _ascii_filename_fallback(filename)
        quoted_filename = quote(filename, safe='')
        filtered_headers['Content-Disposition'] = (
            f'{disposition}; filename="{ascii_filename}"; filename*=UTF-8\'\'{quoted_filename}'
        )

        async def stream_content():
            try:
                async for chunk in upstream_response.content.iter_any():
                    yield chunk
            finally:
                upstream_response.release()
                await session.close()

        return StreamingResponse(
            content=stream_content(),
            status_code=upstream_response.status,
            headers=filtered_headers,
        )

    except Exception:
        await session.close()
        log.exception('Terminal file content proxy error')
        return JSONResponse(
            {'error': 'Terminal file request failed'},
            status_code=502,
            headers={
                'Cache-Control': 'private, no-store',
                'X-Content-Type-Options': 'nosniff',
            },
        )


@router.api_route('/{server_id}/{path:path}', methods=PROXY_METHODS)
async def proxy_terminal(
    server_id: str,
    path: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Proxy a request to the admin terminal server identified by *server_id*."""
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        return JSONResponse({'error': f"Terminal server '{server_id}' not found"}, status_code=404)

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
    if not await has_connection_access(user, connection, user_group_ids):
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
    # Forward per-session cwd tracking header
    session_id = request.headers.get('x-session-id')
    if session_id:
        headers['X-Session-Id'] = session_id
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
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        upstream_content_type = upstream_response.headers.get('content-type', '')
        filtered_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() not in STRIPPED_RESPONSE_HEADERS
        }
        if TERMINAL_PROXY_HEADERS:
            filtered_headers.update(TERMINAL_PROXY_HEADERS)

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
        user = await Users.get_user_by_id(data['id'])
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
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        await ws.close(code=4004, reason='Terminal server not found')
        return None

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
    if not await has_connection_access(user, connection, user_group_ids):
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

    # Encode session_id as an opaque path segment so it cannot smuggle '?'/'#'/'&' (at any
    # decode depth) and inject an attacker-chosen user_id ahead of the one appended below.
    safe_session_id = urllib.parse.quote(session_id, safe='')

    if policy_id:
        upstream_url = f'{ws_base}/p/{policy_id}/api/terminals/{safe_session_id}'
    else:
        upstream_url = f'{ws_base}/api/terminals/{safe_session_id}'
    if upstream_params:
        upstream_url += f'?{urllib.parse.urlencode(upstream_params)}'

    app = ws.scope.get('app')
    opened = False
    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(upstream_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as upstream:
            import asyncio
            import json as _json

            # First-message auth to upstream terminal server
            auth_type = connection.get('auth_type', 'bearer')
            if auth_type == 'bearer':
                key = connection.get('key', '')
                await upstream.send_str(_json.dumps({'type': 'auth', 'token': key}))

            await publish_event(
                app,
                EVENTS.TERMINAL_SESSION_OPENED,
                actor=user,
                subject_id=session_id,
                subject_type='terminal.session',
                data={'server_id': server_id},
            )
            opened = True

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

            # End the proxy as soon as either direction finishes (e.g. a
            # graceful upstream CLOSE) and cancel the sibling, which would
            # otherwise hang on a blocked ws.receive() until the browser leaves.
            tasks = [
                asyncio.create_task(_client_to_upstream()),
                asyncio.create_task(_upstream_to_client()),
            ]
            _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    except Exception as e:
        log.exception('Terminal WebSocket proxy error: %s', e)
    finally:
        await session.close()
        if opened:
            await publish_event(
                app,
                EVENTS.TERMINAL_SESSION_CLOSED,
                actor=user,
                subject_id=session_id,
                subject_type='terminal.session',
                data={'server_id': server_id},
            )
        try:
            await ws.close()
        except Exception:
            pass
