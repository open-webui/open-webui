"""Machines: Open Terminal servers that Open WebUI reaches and proxies.

Mounted at /api/v1/machines.

Routes:
  /ssh/...                       — add, upgrade, restart and remove machines over SSH (admin)
  GET  /                         — list machines the user has access to
  *    /{server_id}/{path:path}  — proxy request to the machine's Open Terminal
"""

import asyncio
import json
import logging
import re
from contextlib import suppress
from html import escape
import posixpath
from urllib.parse import quote, unquote, urljoin, urlsplit

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from multidict import CIMultiDict
from open_webui.config import MACHINE_PROXY_HEADERS
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, ENABLE_TOOL_SERVERS
from open_webui.events import EVENTS, publish_event
from open_webui.models.groups import Groups
from open_webui.routers.templates import router as templates_router
from open_webui.utils.access_control import has_connection_access
from open_webui.utils.auth import get_admin_user, get_verified_user, get_verified_user_by_token
from open_webui.utils.browser import browser_access, create_browser_token
from open_webui.utils.tether import RelayInterrupted, get_machine_connections
from open_webui.utils.headers import bearer_auth_header, normalize_bearer_token
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.machines import MachineError, managed, local as local_machines, ssh as ssh_machines
from open_webui.utils.machines.managed import describe
from open_webui.utils.machines import (
    get_machine_client,
    find_machine_connection,
    machine_headers,
    get_machine_url,
    machine_chat_uploads,
)
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect
from yarl import URL

log = logging.getLogger(__name__)

router = APIRouter()
router.include_router(templates_router, prefix='/templates')

STREAMING_CONTENT_TYPES = ('application/octet-stream', 'image/', 'application/pdf', 'text/event-stream')
ADMIN_API_PATHS = ('api/v1/policies', 'api/v1/status', 'api/v1/terminals')
# Drop the upstream's server and date: uvicorn adds its own and forwarding both duplicates them.
STRIPPED_RESPONSE_HEADERS = frozenset(
    ('transfer-encoding', 'connection', 'content-encoding', 'content-length', 'server', 'date')
)


# ---------------------------------------------------------------------------
# Managed machines (admin): Open WebUI installs Open Terminal on a machine it reaches by SSH,
# or on this computer (experimental). /managed/{id}/... works for both kinds.
# Registered before the /{server_id}/... proxy routes so they are not forwarded upstream.
# ---------------------------------------------------------------------------

_ssh_tasks: set[asyncio.Task] = set()  # keep provisioning tasks referenced until they finish

SSH_HOST = r'^[A-Za-z0-9.\-:\[\]]{1,253}$'
SSH_USER = r'^[a-z_][a-z0-9_.\-]{0,31}$'
SSH_MACHINE_ID = r'^m_[0-9a-f]{8}$'


class SSHTarget(BaseModel):
    host: str = Field(pattern=SSH_HOST)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(pattern=SSH_USER)


class Pinned(SSHTarget):
    host_key: str = Field(pattern=r'^ssh-[a-z0-9-]+ [A-Za-z0-9+/=]+$|^ecdsa-sha2-nistp\d+ [A-Za-z0-9+/=]+$')


class InstallKeyForm(Pinned):
    id: str = Field(pattern=SSH_MACHINE_ID)
    public_key: str
    # One of these logs in once to add Open WebUI's key. Neither is stored.
    password: str = Field('', max_length=1024)
    private_key: str = Field('', max_length=16384)
    passphrase: str = Field('', max_length=1024)


class CreateForm(Pinned):
    id: str = Field(pattern=SSH_MACHINE_ID)
    name: str = Field('', max_length=100)
    version: str = Field('latest', max_length=20)  # 'latest' or an exact Open Terminal version
    # For `open-terminal install-deps`: dependency sets it knows by name, and apt packages. Needs passwordless sudo.
    deps: list[str] = Field(default_factory=list, max_length=16)
    packages: list[str] = Field(default_factory=list, max_length=64)


class LocalForm(BaseModel):
    id: str = Field(pattern=SSH_MACHINE_ID)  # picked by the browser so it can follow progress from the start
    name: str = Field('', max_length=100)
    version: str = Field('latest', max_length=20)
    folder: str = Field('', max_length=1024)  # empty: the project folder Open WebUI picks


class UpgradeForm(BaseModel):
    version: str | None = Field(None, max_length=20)  # omitted: keep the machine's current choice
    deps: list[str] | None = Field(None, max_length=16)
    packages: list[str] | None = Field(None, max_length=64)


class InstallForm(BaseModel):
    deps: list[str] = Field(default_factory=list, max_length=16)
    packages: list[str] = Field(default_factory=list, max_length=64)


class FolderForm(BaseModel):
    folder: str = Field('', max_length=1024)  # empty: the default (home over SSH)


def _ssh_fail(error: BaseException):
    status = 404 if str(error) == 'Unknown machine.' else 400
    raise HTTPException(status, describe(error))


def _ssh_start(coroutine):
    task = asyncio.create_task(coroutine)
    _ssh_tasks.add(task)
    task.add_done_callback(_ssh_tasks.discard)


@router.post('/ssh/keypair')
async def create_keypair(user=Depends(get_admin_user)):
    machine_id, public_key = await ssh_machines.new_keypair()
    return {'id': machine_id, 'public_key': public_key}


@router.post('/ssh/probe')
async def probe(form: SSHTarget, user=Depends(get_admin_user)):
    try:
        host_key, fingerprint = await ssh_machines.probe_host_key(form.host, form.port)
    except (TimeoutError, MachineError, OSError) as error:
        _ssh_fail(error)
    return {'host_key': host_key, 'fingerprint': fingerprint}


@router.post('/ssh/install-key')
async def install_key(form: InstallKeyForm, user=Depends(get_admin_user)):
    try:
        await ssh_machines.install_public_key(
            form.model_dump(include={'host', 'port', 'username', 'host_key'}),
            form.id,
            form.public_key,
            password=form.password,
            private_key=form.private_key,
            passphrase=form.passphrase,
        )
    except Exception as error:
        _ssh_fail(error)
    return {'status': True}  # the password or private key is not stored anywhere


@router.post('/ssh')
async def create_machine(request: Request, form: CreateForm, user=Depends(get_admin_user)):
    try:
        version = managed.requested_version(form.version)
        managed.install_args(form.deps, form.packages)
    except MachineError as error:
        _ssh_fail(error)
    target = form.model_dump(include={'host', 'port', 'username', 'host_key'})
    _ssh_start(
        managed.provision(
            request,
            form.id,
            user.id,
            name=form.name or form.host,
            target=target,
            version=version,
            deps=form.deps,
            packages=form.packages,
        )
    )
    return {'id': form.id, 'status': 'installing'}


@router.get('/local')
async def get_local_machine_defaults(user=Depends(get_admin_user)):
    """What adding this computer would do: where sessions start by default, and whether it is already added."""
    connections = await managed.list_connections()
    return {
        'folder': local_machines.default_folder(),
        'added': any(managed.kind(c) == 'local' for c in connections),
    }


@router.post('/local')
async def create_local_machine(request: Request, form: LocalForm, user=Depends(get_admin_user)):
    """Install Open Terminal on the computer Open WebUI runs on. Experimental; single instance only."""
    connections = await managed.list_connections()
    if any(managed.kind(c) == 'local' for c in connections):
        raise HTTPException(409, 'A local machine is already added.')
    if any(c.get('id') == form.id for c in connections):
        raise HTTPException(409, 'A machine with this id already exists.')
    try:
        version = managed.requested_version(form.version)
        folder = managed.clean_folder(form.folder) or None
    except MachineError as error:
        _ssh_fail(error)
    _ssh_start(
        managed.provision(request, form.id, user.id, name=form.name, is_local=True, version=version, folder=folder)
    )
    return {'id': form.id, 'status': 'installing'}


@router.post('/managed/{machine_id}/upgrade')
async def upgrade_machine(
    request: Request, machine_id: str, form: UpgradeForm | None = None, user=Depends(get_admin_user)
):
    """Install the machine's chosen Open Terminal version again ('latest' fetches the newest); also repairs."""
    try:
        await managed.get_machine(machine_id)
        version = managed.requested_version(form.version) if form and form.version is not None else None
        managed.install_args(form.deps if form else None, form.packages if form else None)
    except MachineError as error:
        _ssh_fail(error)
    _ssh_start(
        managed.provision(
            request,
            machine_id,
            user.id,
            version=version,
            deps=form.deps if form else None,
            packages=form.packages if form else None,
        )
    )
    return {'id': machine_id, 'status': 'installing'}


@router.post('/managed/{machine_id}/install')
async def install_machine_packages(request: Request, machine_id: str, form: InstallForm, user=Depends(get_admin_user)):
    """Install system packages on the machine through `open-terminal install-deps`. Needs passwordless sudo."""
    try:
        await managed.get_machine(machine_id)
        if not managed.install_args(form.deps, form.packages):
            raise MachineError('Enter what to install.')
    except MachineError as error:
        _ssh_fail(error)
    _ssh_start(managed.install(request, machine_id, user.id, form.deps, form.packages))
    return {'id': machine_id, 'status': 'installing'}


@router.post('/managed/{machine_id}/folder')
async def set_machine_folder(machine_id: str, form: FolderForm, user=Depends(get_admin_user)):
    """Change where terminal sessions start, then restart Open Terminal there."""
    try:
        await managed.set_folder(machine_id, form.folder)
    except Exception as error:
        _ssh_fail(error)
    return {'status': True}


@router.post('/managed/{machine_id}/restart')
async def restart_machine(machine_id: str, user=Depends(get_admin_user)):
    try:
        await managed.restart(machine_id)
    except Exception as error:
        _ssh_fail(error)
    return {'status': True}


@router.get('/managed/{machine_id}/logs')
async def machine_logs(machine_id: str, lines: int = 200, user=Depends(get_admin_user)):
    try:
        return {'logs': await managed.logs(machine_id, min(max(lines, 1), 2000))}
    except Exception as error:
        _ssh_fail(error)


@router.delete('/managed/{machine_id}')
async def uninstall_machine(machine_id: str, force: bool = False, user=Depends(get_admin_user)):
    """Uninstall from the machine and remove it. With force, remove it even if the machine is unreachable."""
    try:
        await managed.uninstall(machine_id)
    except Exception as error:
        if not force or str(error) == 'Unknown machine.':
            _ssh_fail(error)
        await managed.remove(machine_id)
    return {'status': True}


def _port_browser_html(body: bytes, prefix: str, port: int) -> bytes:
    """Keep port links inside the proxy and report navigation from sandboxed frames."""
    config = json.dumps({'prefix': prefix, 'origin': f'http://localhost:{port}'}).replace('<', '\\u003c')
    script = r"""
(() => {
  const config = __CONFIG__;
  const remote = (value = location.href) => {
    const url = new URL(value, location.href);
    return url.pathname.startsWith(config.prefix)
      ? config.origin + '/' + url.pathname.slice(config.prefix.length) + url.search + url.hash
      : url.href;
  };
  const destination = value => new URL(value, remote());
  const proxy = value => {
    const url = destination(value);
    return url.origin === config.origin ? config.prefix + url.pathname.slice(1) + url.search + url.hash : url.href;
  };
  const report = () => parent.postMessage({type: 'terminal-browser-state', url: remote(), title: document.title}, '*');
  for (const method of ['pushState', 'replaceState']) {
    const original = history[method].bind(history);
    history[method] = (state, title, value) => {
      try { const result = original(state, title, value == null ? value : proxy(value)); queueMicrotask(report); return result; }
      catch (error) {
        if (error.name !== 'SecurityError' || value == null) throw error;
        parent.postMessage({type: 'terminal-browser-navigate', url: destination(value).href, replace: method === 'replaceState'}, '*');
      }
    };
  }
  addEventListener('popstate', report);
  addEventListener('hashchange', report);
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.hasAttribute('download')) return;
    const url = destination(remote(link.href));
    if (!/^https?:$/.test(url.protocol)) return;
    event.preventDefault();
    parent.postMessage({type: 'terminal-browser-navigate', url: url.href}, '*');
  }, true);
  document.addEventListener('submit', event => {
    const form = event.target;
    if (form instanceof HTMLFormElement) form.action = proxy(form.getAttribute('action') || remote());
  }, true);
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init) => nativeFetch(input instanceof Request ? new Request(proxy(input.url), input) : proxy(input), init);
  const nativeOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) { return nativeOpen.call(this, method, proxy(url), ...rest); };
  addEventListener('DOMContentLoaded', () => {
    new MutationObserver(report).observe(document.querySelector('title') || document.head || document.documentElement, {childList:true,subtree:true,characterData:true});
    report();
  });
  report();
})();
""".replace('__CONFIG__', config)
    html = body.decode('utf-8', errors='replace')
    # Root-relative assets otherwise resolve against WebUI instead of the port.
    html = re.sub(
        r"""(\b(?:href|src|action)\s*=\s*["'])/(?!/)""",
        lambda match: match[1] + escape(prefix, quote=True),
        html,
        flags=re.I,
    )
    bridge = '<script>' + script + '</script>'
    head = re.search(r'<head\b[^>]*>', html, re.I)
    if head:
        html = html[: head.end()] + bridge + html[head.end() :]
    else:
        html = bridge + html
    return html.encode('utf-8')


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
    # URL parsers also remove tabs/newlines, which can turn '.\t.' into '..'.
    if any(char in decoded for char in '\\\t\r\n'):
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


@router.api_route(
    '/{server_id}/browser/view/{sid}/{browser_token}/{path:path}',
    methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
)
async def browser_http(request: Request, server_id: str, sid: str, browser_token: str, path: str):
    user, data = await browser_access(server_id, sid, browser_token)
    if data.get('resource') == 'files':
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            raise HTTPException(405, 'File preview tokens are read-only')
        file_path = _sanitize_proxy_path(path)
        if file_path is None:
            raise HTTPException(400, 'Invalid file path')
        path = f'files/serve/{file_path}'
    else:
        path = f'browser/view/{sid}/{data["capability"]}/{path}'
    return await _proxy_machine(
        server_id,
        path,
        request,
        user,
        context=browser_context(data),
        browser_auth=data['relay'],
    )


async def relay_from_browser(ws, upstream):
    while True:
        msg = await ws.receive()
        if msg['type'] == 'websocket.disconnect':
            return
        if msg.get('bytes') is not None:
            await upstream.send_bytes(msg['bytes'])
        elif msg.get('text') is not None:
            await upstream.send_str(msg['text'])


async def relay_to_browser(ws, upstream):
    async for msg in upstream:
        if msg.type == aiohttp.WSMsgType.TEXT:
            await ws.send_text(msg.data)
        elif msg.type == aiohttp.WSMsgType.BINARY:
            await ws.send_bytes(msg.data)
        else:
            return
    code = upstream.close_code or 1011
    await ws.close(code=1011 if code in (1005, 1006, 1015) else code)


async def watch_access(server_id, sid, browser_token, request):
    while True:
        await asyncio.sleep(10)
        current_user, data = await browser_access(server_id, sid, browser_token)
        current = await find_machine_connection(current_user, server_id, browser_context(data), request=request)
        if not current:
            return


@router.websocket('/{server_id}/browser/view/{sid}/{browser_token}/{kind}')
async def browser_ws(ws: WebSocket, server_id: str, sid: str, browser_token: str, kind: str):
    try:
        user, data = await browser_access(server_id, sid, browser_token)
        connection = await find_machine_connection(user, server_id, browser_context(data), request=ws)
        if (
            kind not in ('ws', 'stream', 'vnc')
            or data.get('resource') == 'files'
            or not ENABLE_TOOL_SERVERS
            or not connection
        ):
            raise HTTPException(403, 'Browser access denied')
        chat = data.get('chat', '')
    except HTTPException:
        await ws.close(code=4001)
        return
    await ws.accept()
    base = get_machine_url(connection).replace('https://', 'wss://').replace('http://', 'ws://')
    url = f'{base}/browser/view/{sid}/{quote(data["capability"], safe="")}/{kind}'
    headers = {'X-User-Id': user.id, 'X-Session-Id': chat, **machine_headers(connection)}
    if data['relay'].get('authorization'):
        headers['Authorization'] = data['relay']['authorization']
    tasks = []
    try:
        async with get_machine_client(
            base,
            connection.get('instance_user_id', user.id),
            service=connection.get('service', 'open_terminal'),
            cookies=data['relay'].get('cookies', {}),
            trust_env=True,
        ) as client:
            async with client.ws_connect(
                url,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                max_msg_size=16 * 1024 * 1024,
            ) as upstream:
                tasks = [
                    asyncio.create_task(relay_from_browser(ws, upstream)),
                    asyncio.create_task(relay_to_browser(ws, upstream)),
                    asyncio.create_task(watch_access(server_id, sid, browser_token, ws)),
                ]
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except aiohttp.WSServerHandshakeError as exc:
        await ws.close(code=4004 if exc.status in (401, 403, 404) else 1011)
    except Exception as exc:
        log.debug('Browser relay disconnected: %s', type(exc).__name__)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        with suppress(Exception):
            await ws.close(code=1011)


@router.get('/')
async def list_machines(request: Request, user=Depends(get_verified_user)):
    """Return terminal servers the authenticated user has access to."""
    if not ENABLE_TOOL_SERVERS:
        return []

    connections = await get_machine_connections(user)
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}

    return [
        {
            'id': connection.get('id', ''),
            'url': '' if connection.get('owner_id') else connection.get('url', ''),
            'name': connection.get('name', ''),
            'template_id': connection.get('template_id'),
            'scope': connection.get('scope'),
            'config': {'chat_uploads': machine_chat_uploads(connection)},
        }
        for connection in connections
        if connection.get('enabled', True)
        and (connection.get('template_id') or await has_connection_access(user, connection, user_group_ids))
    ]


PROXY_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']


@router.api_route('/{server_id}/{path:path}', methods=PROXY_METHODS)
# Register the chat route before the catch-all.
@router.api_route('/{server_id}/chats/{chat_id}/{path:path}', methods=PROXY_METHODS)
async def proxy_machine(
    server_id: str,
    path: str,
    request: Request,
    user=Depends(get_verified_user),
):
    return await _proxy_machine(
        server_id,
        path,
        request,
        user,
        context={
            'instance_user_id': request.headers.get('x-terminal-user-id'),
            'chat_id': request.path_params.get('chat_id') or request.headers.get('x-session-id'),
            'model_id': request.headers.get('x-terminal-model-id'),
        },
    )


async def _proxy_machine(server_id, path, request, user, *, context, browser_auth=None):
    if not ENABLE_TOOL_SERVERS:
        return JSONResponse({'error': 'Tool servers are disabled'}, status_code=403)

    connection = await find_machine_connection(user, server_id, context, request=request)

    if connection is None:
        return JSONResponse({'error': f"Machine '{server_id}' not found"}, status_code=404)

    base_url = get_machine_url(connection)
    if not base_url:
        return JSONResponse({'error': 'Machine URL not configured'}, status_code=503)

    safe_path = _sanitize_proxy_path(path)
    if safe_path is None:
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    target_url = f'{base_url}/{safe_path}'

    # Check the path aiohttp will send, relative to the configured server root.
    base_path = URL(str(connection.get('url') or '')).path.rstrip('/')
    target_path = URL(target_url).path
    if any(
        target_path == f'{base_path}/{prefix}' or target_path.startswith(f'{base_path}/{prefix}/')
        for prefix in ADMIN_API_PATHS
    ):
        return JSONResponse({'error': 'Path not allowed'}, status_code=403)

    if request.query_params:
        target_url += f'?{request.query_params}'

    headers = {'X-User-Id': user.id}
    # Forward per-session cwd tracking header
    session_id = context.get('chat_id')
    if session_id:
        headers['X-Session-Id'] = session_id
    cookies = getattr(request, 'cookies', {}) if connection.get('forward_cookies', False) else {}
    auth_type = connection.get('auth_type', 'bearer')

    if browser_auth is not None:
        cookies = browser_auth.get('cookies', {})
        if browser_auth.get('authorization'):
            headers['Authorization'] = browser_auth['authorization']
    elif auth_type == 'bearer':
        headers.update(bearer_auth_header(connection.get('key', '')))
    elif auth_type == 'session':
        headers.update(bearer_auth_header(request.state.token.credentials))
    elif auth_type == 'system_oauth':
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

    if browser_auth is not None:
        for name in (
            'accept',
            'origin',
            'access-control-request-method',
            'access-control-request-headers',
            'last-event-id',
            'range',
        ):
            if value := request.headers.get(name):
                headers[name] = value

    headers.update(machine_headers(connection))
    content_type = request.headers.get('content-type')
    if content_type:
        headers['Content-Type'] = content_type

    if connection.get('template_id') and safe_path == 'files/preview' and request.method == 'POST':
        browser_token = create_browser_token(
            server_id,
            user.id,
            context.get('instance_user_id'),
            session_id or '',
            {'id': 'files', 'token': ''},
            headers,
            cookies,
            resource='files',
        )
        base = request.url.path.removesuffix('/files/preview')
        return {'url': f'{base}/browser/view/files/{quote(browser_token, safe="")}/'}

    session = get_machine_client(
        base_url,
        connection.get('instance_user_id', user.id),
        service=connection.get('service', 'open_terminal'),
        timeout=aiohttp.ClientTimeout(total=300, connect=10),
        trust_env=True,
    )

    try:
        has_body = 'content-length' in request.headers or 'transfer-encoding' in request.headers
        body = request.stream() if has_body else None

        upstream_response = await session.request(
            method=request.method,
            url=target_url,
            headers=headers,
            cookies=cookies,
            data=body or None,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            allow_redirects=False,
        )

        upstream_content_type = upstream_response.headers.get('content-type', '')
        # Case-insensitive and multi-valued, like the upstream headers: admin headers replace the
        # machine's whatever their case, and repeated headers such as Set-Cookie all survive.
        filtered_headers = CIMultiDict(
            (key, value)
            for key, value in upstream_response.headers.items()
            if key.lower() not in STRIPPED_RESPONSE_HEADERS
        )
        filtered_headers.update(MACHINE_PROXY_HEADERS)

        port_match = re.match(r'^proxy/(\d+)/', safe_path)
        port_prefix = None
        if port_match:
            port_prefix = request.url.path[: request.url.path.index('/proxy/') + len(port_match[0]) + 1]
            location = upstream_response.headers.get('location')
            if location:
                remote_origin = f'http://localhost:{port_match[1]}'
                destination = urlsplit(urljoin(f'{remote_origin}/{safe_path[len(port_match[0]) :]}', location))
                if destination.netloc == urlsplit(remote_origin).netloc:
                    filtered_headers['Location'] = (
                        port_prefix
                        + destination.path.lstrip('/')
                        + (f'?{destination.query}' if destination.query else '')
                        + (f'#{destination.fragment}' if destination.fragment else '')
                    )

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
        if (
            safe_path.startswith('browser/sessions')
            and upstream_response.status < 300
            and request.method in ('GET', 'POST', 'PATCH')
        ):
            browser_session = json.loads(response_body)
            if isinstance(browser_session, dict) and browser_session.get('id') and browser_session.get('token'):
                browser_session['token'] = create_browser_token(
                    server_id,
                    user.id,
                    context.get('instance_user_id'),
                    session_id or '',
                    browser_session,
                    headers,
                    cookies,
                )
                response_body = json.dumps(browser_session).encode()
        if port_prefix and 'text/html' in upstream_content_type:
            response_body = _port_browser_html(response_body, port_prefix, int(port_match[1]))
        status_code = upstream_response.status
        await upstream_response.release()
        await session.close()

        return Response(content=response_body, status_code=status_code, headers=filtered_headers)

    except ClientDisconnect:
        await session.close()
        return Response(status_code=499)
    except RelayInterrupted as error:
        await session.close()
        return JSONResponse(error.result(), status_code=502)
    except (aiohttp.ClientConnectionError, TimeoutError) as error:
        await session.close()
        log.error('Terminal proxy error: %s', str(error) or type(error).__name__)
        return JSONResponse({'error': f'Machine proxy error: {error}'}, status_code=502)
    except Exception as error:
        await session.close()
        log.exception('Terminal proxy error: %s', error)
        return JSONResponse({'error': f'Machine proxy error: {error}'}, status_code=502)


# WebSocket proxy for interactive terminal sessions


async def _resolve_authenticated_connection(ws: WebSocket, server_id: str):
    """Authenticate a WebSocket via first-message auth and resolve the terminal server.

    The client must send ``{"type": "auth", "token": "<jwt>"}`` as its first
    message after connecting.

    Returns ``(user, connection, chat_id, token)`` on success, or ``None`` after
    closing *ws* with an appropriate error code.
    """
    # First-message authentication
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        payload = JSONCodec.loads(raw)
        if payload.get('type') != 'auth':
            await ws.close(code=4001, reason='Expected auth message')
            return None
        token = payload.get('token', '')
    except (TimeoutError, JSONCodec.JSONDecodeError):
        await ws.close(code=4001, reason='Auth timeout or invalid payload')
        return None
    except WebSocketDisconnect:
        return None
    except Exception:
        await ws.close(code=4001, reason='Invalid token')
        return None

    ws.state.auth = payload
    result = await _resolve_machine_access(ws, server_id, token)
    if result is None:
        return None
    user, connection = result
    chat_id = payload.get('chat_id', '')
    return user, connection, chat_id if isinstance(chat_id, str) else '', token


async def _resolve_machine_access(ws: WebSocket, server_id: str, token: str):
    """Resolve current access for both the handshake and an open terminal session."""
    if not ENABLE_TOOL_SERVERS:
        await ws.close(code=4003, reason='Tool servers are disabled')
        return None

    try:
        user = await get_verified_user_by_token(token, getattr(ws.app.state, 'redis', None))
        if user is None:
            await ws.close(code=4001, reason='Invalid token')
            return None
    except Exception:
        await ws.close(code=4001, reason='Invalid token')
        return None

    # Resolve the machine
    try:
        connection = await find_machine_connection(user, server_id, socket_metadata(ws), request=ws)
    except HTTPException as exc:
        await ws.close(code=4003, reason=str(exc.detail))
        return None

    if connection is None:
        if server_id.startswith('tether:'):
            await ws.close(code=1013, reason='Tether is offline. Reconnecting.')
        else:
            await ws.close(code=4004, reason='Machine not found')
        return None

    return user, connection


@router.websocket('/{server_id}/events')
async def ws_events(ws: WebSocket, server_id: str):
    await _proxy_terminal_websocket(ws, server_id)


@router.websocket('/{server_id}/desktop/stream')
async def desktop_ws(ws: WebSocket, server_id: str):
    await _proxy_terminal_websocket(ws, server_id, stream_path='desktop/stream')


@router.websocket('/{server_id}/desktop/audio')
async def desktop_audio_ws(ws: WebSocket, server_id: str):
    await _proxy_terminal_websocket(ws, server_id, stream_path='desktop/audio')


@router.websocket('/{server_id}/execute')
async def ws_processes(ws: WebSocket, server_id: str):
    await _proxy_terminal_websocket(ws, server_id, stream_path='execute')


@router.websocket('/{server_id}/execute/{process_id}/status')
async def ws_process_output(ws: WebSocket, server_id: str, process_id: str):
    from urllib.parse import quote

    await _proxy_terminal_websocket(ws, server_id, stream_path=f'execute/{quote(process_id, safe="")}/status')


@router.websocket('/{server_id}/api/terminals/{session_id}')
async def ws_terminal(ws: WebSocket, server_id: str, session_id: str):
    await _proxy_terminal_websocket(ws, server_id, session_id)


async def _proxy_terminal_websocket(
    ws: WebSocket,
    server_id: str,
    session_id: str | None = None,
    stream_path: str = 'events',
):
    """Proxy terminal sessions and filesystem notifications to a terminal server.

    Uses first-message auth: the client sends ``{"type": "auth", "token": "<jwt>"}``
    as its first message. The proxy validates the JWT, then connects to the
    upstream terminal server using the configured terminal auth mode.
    """
    await ws.accept()

    result = await _resolve_authenticated_connection(ws, server_id)
    if result is None:
        return
    user, connection, chat_id, token = result

    base_url = get_machine_url(connection)
    if not base_url:
        await ws.close(code=4003, reason='Machine URL not configured')
        return

    # Build upstream WebSocket URL (no token in URL)
    ws_base = base_url.replace('https://', 'wss://').replace('http://', 'ws://')

    upstream_params = {}
    # For orchestrator-backed servers, pass user_id
    upstream_params['user_id'] = connection.get('instance_user_id', user.id)
    if stream_path.startswith('execute/'):
        for key in ('offset', 'tail'):
            if key in ws.query_params:
                upstream_params[key] = ws.query_params[key]
    upstream_headers = {'X-User-Id': user.id, 'X-Session-Id': chat_id, **machine_headers(connection)}
    import urllib.parse

    # Encode session_id as an opaque path segment so it cannot smuggle '?'/'#'/'&' (at any
    # decode depth) and inject an attacker-chosen user_id ahead of the one appended below.
    upstream_path = (
        f'api/terminals/{urllib.parse.quote(session_id, safe="")}' if session_id is not None else stream_path
    )
    upstream_url = f'{ws_base}/{upstream_path}'
    if upstream_params:
        upstream_url += f'?{urllib.parse.urlencode(upstream_params)}'

    request = Request({**ws.scope, 'type': 'http', 'method': 'GET'})
    opened = False
    session = get_machine_client(
        base_url, connection.get('instance_user_id', user.id), service=connection.get('service', 'open_terminal')
    )
    try:
        async with session.ws_connect(
            upstream_url,
            headers=upstream_headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as upstream:
            import json as _json

            # First-message auth to the machine's Open Terminal
            auth_type = connection.get('auth_type', 'bearer')
            if auth_type == 'bearer':
                key = normalize_bearer_token(connection.get('key', ''))
                await upstream.send_str(_json.dumps({**ws.state.auth, 'token': key}))
            else:
                await upstream.send_str(_json.dumps({**ws.state.auth, 'token': ''}))

            if session_id is not None:
                await publish_event(
                    request,
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
                    with suppress(Exception):
                        await ws.close(code=1011, reason='Terminal connection interrupted. Reconnecting.')

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
                    code = upstream.close_code or 1011
                    await ws.close(code=1011 if code in (1005, 1006, 1015) else code)
                except Exception:
                    with suppress(Exception):
                        await ws.close(code=1011, reason='Terminal connection interrupted. Reconnecting.')

            async def _watch_access():
                try:
                    while True:
                        # Poll current state so revocation also works across workers.
                        await asyncio.sleep(10)
                        if await _resolve_machine_access(ws, server_id, token) is None:
                            return
                except Exception:
                    log.exception('Terminal access recheck failed')
                    with suppress(Exception):
                        await ws.close(code=1011, reason='Terminal access check unavailable. Reconnecting.')

            # End the proxy as soon as any task finishes (e.g. a
            # graceful upstream CLOSE) and cancel the rest, which would
            # otherwise hang on a blocked ws.receive() until the browser leaves.
            tasks = [
                asyncio.create_task(_client_to_upstream()),
                asyncio.create_task(_upstream_to_client()),
                asyncio.create_task(_watch_access()),
            ]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        log.exception('Terminal WebSocket proxy error: %s', e)
        status = getattr(e, 'status', getattr(e, 'status_code', None))
        code = {401: 4001, 403: 4003, 404: 4004}.get(status, 1011)
        with suppress(Exception):
            await ws.close(code=code)
    finally:
        await session.close()
        if opened:
            await publish_event(
                request,
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


def browser_context(data):
    return {'instance_user_id': data.get('instance_user'), 'chat_id': data.get('chat'), 'model_id': data.get('model')}


def socket_metadata(ws):
    auth = getattr(ws.state, 'auth', {})
    return {
        'instance_user_id': auth.get('instance_user_id'),
        'chat_id': auth.get('chat_id'),
        'model_id': auth.get('model_id'),
    }
