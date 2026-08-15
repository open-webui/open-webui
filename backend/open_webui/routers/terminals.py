"""Reverse proxy for admin-configured terminal servers.

Routes:
  GET  /                                                         — list terminals the user has access to
  POST /{server_id}/port-preview/{port}                          — mint a port preview credential
  *    /{server_id}/port-preview/{port}/{preview_token}/{path}   — serve a port, sandboxed
  *    /{server_id}/{path:path}                                  — proxy request to terminal server
"""

import datetime as dt
import hashlib
import logging
import posixpath
from urllib.parse import unquote

import aiohttp
import jwt
from fastapi import APIRouter, Depends, Request, Response, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from open_webui.config import TERMINAL_PROXY_HEADERS
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.events import EVENTS, publish_event
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.utils.access_control import has_connection_access
from open_webui.utils.auth import (
    ALGORITHM,
    SESSION_SECRET,
    decode_token,
    get_verified_user,
    get_verified_user_by_id,
    is_valid_token,
)
from open_webui.utils.headers import bearer_auth_header, normalize_bearer_token
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.security_headers import MANAGED_HEADER_NAMES
from open_webui.utils.terminals import (
    TERMINAL_CONTEXT_HEADER,
    get_terminal_server_url,
    is_terminal_orchestrator,
    terminal_context_available,
    terminal_context_config,
    terminal_context_id,
    terminal_chat_uploads,
    terminal_contexts,
)
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect

log = logging.getLogger(__name__)

router = APIRouter()

STREAMING_CONTENT_TYPES = ('application/octet-stream', 'image/', 'application/pdf')
STRIPPED_RESPONSE_HEADERS = frozenset(
    (
        'transfer-encoding',
        'connection',
        'content-encoding',
        'content-length',
        # Responses come back on our own origin, so a terminal server writing cookies or clearing
        # site data here would be doing it to the application.
        'set-cookie',
        'clear-site-data',
    )
)

PORT_PREVIEW_TTL = dt.timedelta(hours=1)
# The preview credential travels in a URL the previewed page can read, so it is signed with its own
# key: presented anywhere else it fails signature verification rather than authenticating a session.
PORT_PREVIEW_SECRET = hashlib.sha256(f'{SESSION_SECRET}:terminal-port-preview'.encode()).hexdigest()
# A port server's response is written by whoever uses the terminal, so it must never run with the
# application's own privileges. The sandbox denies it the application origin; the credential rides in
# the URL instead of a cookie because a sandboxed document is no longer same-site with the application.
PORT_PREVIEW_HEADERS = {
    'Content-Security-Policy': 'sandbox allow-scripts allow-forms allow-popups allow-modals allow-downloads',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'no-store',
    # The preview loads at an opaque origin, so its own assets are cross-origin to it and an
    # operator's stricter default would leave the page unable to load anything it references.
    'Cross-Origin-Resource-Policy': 'cross-origin',
}


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
    # posixpath splits on '/' only, so 'a/..\..\b' survives normpath as one component.
    # Upstreams that treat '\' as a separator would resolve it, so reject outright.
    if '\\' in decoded:
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
            'contexts': terminal_contexts(connection),
            'config': {'chat_uploads': terminal_chat_uploads(connection)},
        }
        for connection in connections
        if connection.get('enabled', True) and await has_connection_access(user, connection, user_group_ids)
    ]


PROXY_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']


@router.post('/{server_id}/port-preview/{port}')
async def create_port_preview_token(server_id: str, port: int, request: Request, user=Depends(get_verified_user)):
    """Mint a credential that authorises previewing one port on one terminal server."""
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((c for c in connections if c.get('id') == server_id and c.get('enabled', True)), None)
    if connection is None or not await has_connection_access(user, connection):
        return JSONResponse({'error': 'Access denied'}, status_code=403)

    # These auth types forward the caller's own credential upstream, and a sandboxed preview carries
    # none, so refuse here rather than serving a page whose every asset then fails.
    if connection.get('auth_type', 'bearer') in ('session', 'system_oauth'):
        return JSONResponse({'error': 'Port preview is unavailable for this terminal server'}, status_code=403)

    # Tied to a session so it can inherit that session's lifetime and revocation. An API key has
    # neither, and nothing in the UI mints this with one.
    session_claims = decode_token(getattr(request.state.token, 'credentials', ''))
    if not session_claims:
        return JSONResponse({'error': 'Port preview requires a session'}, status_code=403)

    now = dt.datetime.now(dt.UTC)
    # Never outlive the session it was minted from, however long that session has left.
    expires_at = now + PORT_PREVIEW_TTL
    session_expiry = session_claims.get('exp')
    if session_expiry:
        expires_at = min(expires_at, dt.datetime.fromtimestamp(session_expiry, dt.UTC))
    token = jwt.encode(
        {
            'user_id': user.id,
            'server_id': server_id,
            'port': port,
            # Carried so signing out, which revokes by jti, revokes the previews minted from it too.
            'session_jti': session_claims.get('jti'),
            'iat': now,
            'exp': expires_at,
        },
        PORT_PREVIEW_SECRET,
        algorithm=ALGORITHM,
    )
    return {'token': token}


@router.api_route('/{server_id}/port-preview/{port}/{preview_token}/{path:path}', methods=PROXY_METHODS)
async def preview_port(server_id: str, port: int, preview_token: str, path: str, request: Request):
    """Serve a port server's response as sandboxed content, authorised by the credential in the path."""
    try:
        claims = jwt.decode(preview_token, PORT_PREVIEW_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return JSONResponse({'error': 'Invalid preview token'}, status_code=403)

    if claims.get('server_id') != server_id or claims.get('port') != port:
        return JSONResponse({'error': 'Invalid preview token'}, status_code=403)

    # The dependency chain is bypassed here, so re-apply what it would have checked: an approved
    # role, and the revocation that signing out and back-channel logout write.
    user = await get_verified_user_by_id(claims.get('user_id'))
    if user is None:
        return JSONResponse({'error': 'Invalid preview token'}, status_code=403)

    revocation_claims = {'id': user.id, 'iat': claims.get('iat'), 'jti': claims.get('session_jti')}
    if not await is_valid_token(revocation_claims, getattr(request.app.state, 'redis', None)):
        return JSONResponse({'error': 'Invalid preview token'}, status_code=403)

    # An empty sub-path is the port's root, which the sanitizer would reject as a bare '.'.
    safe_path = _sanitize_proxy_path(path) if path else ''
    if safe_path is None:
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    response = await _proxy(server_id, f'proxy/{port}/{safe_path}', request, user, sandboxed=True)

    # This response keeps its own security headers, so drop the ones the terminal server sent: they
    # would be a third party deciding what the browser enforces on our origin.
    for name in MANAGED_HEADER_NAMES:
        del response.headers[name]
    response.headers.update(PORT_PREVIEW_HEADERS)
    request.state.owns_security_headers = True
    return response


@router.api_route('/{server_id}/{path:path}', methods=PROXY_METHODS)
async def proxy_terminal(
    server_id: str,
    path: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Proxy a request to the admin terminal server identified by *server_id*."""
    safe_path = _sanitize_proxy_path(path)
    if safe_path is None:
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    # Port traffic is reachable only through preview_port, which sandboxes what comes back. Preview
    # URLs are rejected too, so a malformed one cannot hand its credential to the terminal server.
    if safe_path.lower().startswith(('proxy/', 'port-preview/')):
        return JSONResponse({'error': 'Not found'}, status_code=404)

    return await _proxy(server_id, safe_path, request, user)


async def _proxy(server_id: str, safe_path: str, request: Request, user, sandboxed: bool = False):
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((c for c in connections if c.get('id') == server_id), None)

    if connection is None:
        return JSONResponse({'error': f"Terminal server '{server_id}' not found"}, status_code=404)

    if not connection.get('enabled', True):
        return JSONResponse({'error': 'Terminal server disabled'}, status_code=403)

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
    if not await has_connection_access(user, connection, user_group_ids):
        return JSONResponse({'error': 'Access denied'}, status_code=403)

    # A sandboxed caller carries none of the credentials these auth types forward upstream. The mint
    # refuses them too; this also covers a connection switched to one after a token was issued.
    if sandboxed and connection.get('auth_type', 'bearer') in ('session', 'system_oauth'):
        return JSONResponse({'error': 'Port preview is unavailable for this terminal server'}, status_code=403)

    base_url = get_terminal_server_url(connection)
    if not base_url:
        return JSONResponse({'error': 'Terminal server URL not configured'}, status_code=503)

    target_url = f'{base_url}/{safe_path}'

    if request.query_params:
        target_url += f'?{request.query_params}'

    headers = {'X-User-Id': user.id}
    # Forward per-session cwd tracking header
    session_id = request.headers.get('x-session-id')
    if session_id:
        headers['X-Session-Id'] = session_id
        if not terminal_context_available(connection, 'chat'):
            return JSONResponse({'error': 'Terminal server is not available in chats'}, status_code=403)
        context_id = terminal_context_id(connection, {'chat_id': session_id}, 'chat')
        if terminal_context_config(connection, 'chat').get('context_id') == 'chat_id' and not context_id:
            return JSONResponse({'error': 'A saved chat is required for this terminal'}, status_code=409)
        if context_id:
            headers[TERMINAL_CONTEXT_HEADER] = context_id
    cookies = {}
    auth_type = connection.get('auth_type', 'bearer')

    if auth_type == 'bearer':
        headers.update(bearer_auth_header(connection.get('key', '')))
    elif auth_type == 'session':
        cookies = request.cookies
        headers.update(bearer_auth_header(request.state.token.credentials))
    elif auth_type == 'system_oauth':
        cookies = request.cookies
        # Resolve the token server-side from the caller's OAuth session; never trust a client header.
        oauth_token = None
        try:
            if request.cookies.get('oauth_session_id', None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    request.cookies.get('oauth_session_id', None),
                )
        except Exception as e:
            log.error(f'Error getting OAuth token: {e}')
        if oauth_token:
            headers.update(bearer_auth_header(oauth_token.get('access_token', '')))
    # auth_type == "none": no Authorization header

    content_type = request.headers.get('content-type')
    if content_type:
        headers['Content-Type'] = content_type

    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=300, connect=10),
        trust_env=True,
    )

    try:
        body = await request.body()

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

    except ClientDisconnect:
        await session.close()
        return Response(status_code=499)
    except (aiohttp.ClientConnectionError, TimeoutError) as error:
        await session.close()
        log.error('Terminal proxy error: %s', str(error) or type(error).__name__)
        return JSONResponse({'error': f'Terminal proxy error: {error}'}, status_code=502)
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

    Returns ``(user, connection, chat_id, token)`` on success, or ``None`` after
    closing *ws* with an appropriate error code.
    """
    import asyncio

    from open_webui.utils.auth import get_verified_user_by_token

    # First-message authentication
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        payload = JSONCodec.loads(raw)
        if payload.get('type') != 'auth':
            await ws.close(code=4001, reason='Expected auth message')
            return None
        token = payload.get('token', '')
        user = await get_verified_user_by_token(token, getattr(ws.app.state, 'redis', None))
        if user is None:
            await ws.close(code=4001, reason='Invalid token')
            return None
    except (asyncio.TimeoutError, JSONCodec.JSONDecodeError):
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

    if not connection.get('enabled', True):
        await ws.close(code=4003, reason='Terminal server disabled')
        return None

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
    if not await has_connection_access(user, connection, user_group_ids):
        await ws.close(code=4003, reason='Access denied')
        return None

    chat_id = payload.get('chat_id', '')
    if not terminal_context_available(connection, 'chat'):
        await ws.close(code=4003, reason='Terminal server is not available in chats')
        return None
    return user, connection, chat_id if isinstance(chat_id, str) else '', token


@router.websocket('/{server_id}/api/terminals/{session_id}')
async def ws_terminal(
    ws: WebSocket,
    server_id: str,
    session_id: str,
):
    """Proxy an interactive WebSocket terminal session to a terminal server.

    Uses first-message auth: the client sends ``{"type": "auth", "token": "<jwt>"}``
    as its first message. The proxy validates the JWT, then connects to the
    upstream terminal server using the configured terminal auth mode.
    """
    await ws.accept()

    result = await _resolve_authenticated_connection(ws, server_id)
    if result is None:
        return
    user, connection, chat_id, token = result

    base_url = get_terminal_server_url(connection)
    if not base_url:
        await ws.close(code=4003, reason='Terminal server URL not configured')
        return

    # Build upstream WebSocket URL (no token in URL)
    ws_base = base_url.replace('https://', 'wss://').replace('http://', 'ws://')

    upstream_params = {}
    # For orchestrator-backed servers, pass user_id
    upstream_params['user_id'] = user.id
    context_id = terminal_context_id(connection, {'chat_id': chat_id}, 'chat')
    upstream_headers = {}
    if terminal_context_config(connection, 'chat').get('context_id') == 'chat_id' and not context_id:
        await ws.close(code=4003, reason='A saved chat is required for this terminal')
        return
    if context_id:
        upstream_headers[TERMINAL_CONTEXT_HEADER] = context_id

    import urllib.parse

    # Encode session_id as an opaque path segment so it cannot smuggle '?'/'#'/'&' (at any
    # decode depth) and inject an attacker-chosen user_id ahead of the one appended below.
    safe_session_id = urllib.parse.quote(session_id, safe='')

    upstream_url = f'{ws_base}/api/terminals/{safe_session_id}'
    if upstream_params:
        upstream_url += f'?{urllib.parse.urlencode(upstream_params)}'

    app = ws.scope.get('app')
    opened = False
    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(
            upstream_url,
            headers=upstream_headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as upstream:
            import asyncio
            import json as _json

            # First-message auth to upstream terminal server
            auth_type = connection.get('auth_type', 'bearer')
            if auth_type == 'bearer':
                key = normalize_bearer_token(connection.get('key', ''))
                await upstream.send_str(_json.dumps({'type': 'auth', 'token': key}))
            elif auth_type == 'session' and is_terminal_orchestrator(connection):
                await upstream.send_str(_json.dumps({'type': 'auth', 'token': token}))

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
