"""Machines Open WebUI installs Open Terminal on itself: over SSH, or on this computer.

Both kinds share one install script (bootstrap.sh) and one lifecycle; only how the script
runs differs: ssh.SSHHost runs it over SSH, local.LocalHost on the computer Open WebUI runs
on. Open Terminal listens on a Unix socket (no TCP port). The machine lives in
machines.connections with url ssh://<id> or local://<id>, so every machine feature works
unchanged.
"""

import asyncio
import logging
import re
import secrets
import shlex
import tempfile
import time
from collections import deque
from contextlib import suppress
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
import asyncssh

from open_webui.models.config import Config
from open_webui.utils.machines import MachineError, local, ssh

log = logging.getLogger(__name__)

# Machines install the latest Open Terminal by default, or a version the admin pins.
# This is the oldest one Open WebUI works with (first with `open-terminal bridge`).
MIN_OPEN_TERMINAL_VERSION = '0.17.21'
UV_VERSION = '0.13.9'
CONNECTIONS = 'machines.connections'
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}

TOKENS = {
    'ID': re.compile(r'm_[0-9a-f]{8}'),
    'VERSION': re.compile(r'latest|\d+\.\d+\.\d+'),
    'MIN_VERSION': re.compile(r'\d+\.\d+\.\d+'),
    'UV_VERSION': re.compile(r'\d+\.\d+\.\d+'),
    'API_KEY': re.compile(r'[A-Za-z0-9_-]{32,64}'),
}
BOOTSTRAP = Path(__file__).with_name('bootstrap.sh').read_text()

# Local ends of SSH tunnels. Unix socket paths max out around 104 characters on macOS, so keep this short.
RUN_DIR = Path(tempfile.mkdtemp(prefix='open-webui-', dir='/tmp' if Path('/tmp').is_dir() else None))


def describe(error: BaseException) -> str:
    """Turn failures into something an admin can act on."""
    if isinstance(error, asyncssh.HostKeyNotVerifiable):
        return "The machine's host key changed. Remove and re-add the machine if this is expected."
    if isinstance(error, asyncssh.PermissionDenied):
        return 'SSH login was refused. Check that the key is in ~/.ssh/authorized_keys, or the password is right.'
    if isinstance(error, asyncio.TimeoutError):
        return 'The machine took too long to respond.'
    if isinstance(error, OSError):
        return f'Could not reach the machine: {error.strerror or error}'
    return str(error) or type(error).__name__


def new_id() -> str:
    return f'm_{secrets.token_hex(4)}'


def requested_version(value: str | None) -> str:
    """Normalize the admin's choice: 'latest' (default) or an exact version no older than the minimum."""
    value = (value or '').strip() or 'latest'
    if value == 'latest':
        return value
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise MachineError('Use "latest" or a version like 0.17.21.')
    if tuple(map(int, value.split('.'))) < tuple(map(int, MIN_OPEN_TERMINAL_VERSION.split('.'))):
        raise MachineError(f'Open WebUI needs Open Terminal {MIN_OPEN_TERMINAL_VERSION} or newer.')
    return value


def clean_start_dir(value: str | None) -> str:
    """Where terminal sessions start. Empty means the default (home over SSH)."""
    value = (value or '').strip()
    if value and (not value.startswith('/') or any(c in value for c in '\n\r\0')):
        raise MachineError('Use an absolute path, like /home/me/project.')
    return value


def clean_flags(value: str | None) -> str:
    """Extra flags for `open-terminal run`, quoted for the shell. Open WebUI sets the socket and the key itself."""
    try:
        flags = shlex.split(value or '')
    except ValueError as error:
        raise MachineError(f'Could not read the flags: {error}.') from error
    for flag in flags:
        if flag.split('=')[0] in ('--ipc', '--api-key'):
            raise MachineError(f'Open WebUI sets {flag.split("=")[0]} itself.')
    return shlex.join(flags)


def install_args(deps: list[str] | None, packages: list[str] | None) -> str:
    """Arguments for `open-terminal install-deps`: the dependency sets it knows by name, then apt packages."""
    deps, packages = list(dict.fromkeys(deps or [])), list(dict.fromkeys(packages or []))
    for name in [*deps, *packages]:
        # Names only: these become arguments of a command that installs as root on the machine.
        if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', name):
            raise MachineError(f'"{name}" is not a package name.')
    return ' '.join([*deps, *(f'--package {name}' for name in packages)])


def render(template: str, **values: str) -> str:
    for name, value in values.items():
        if not TOKENS[name].fullmatch(value):
            raise MachineError(f'Refusing to render {name}.')
    return re.sub(r'__OPEN_WEBUI_([A-Z_]+)__', lambda m: values[m.group(1)], template)


# ---------------------------------------------------------------------------
# Stored machines
# ---------------------------------------------------------------------------


def kind(c: dict) -> str | None:
    return 'local' if c.get('local') is not None else 'ssh' if c.get('ssh') is not None else None


def state(c: dict) -> dict:
    return c.get('local') or c.get('ssh') or {}


async def list_connections() -> list[dict]:
    return list(await Config.get(CONNECTIONS, []) or [])


async def get_machine(machine_id: str) -> dict:
    for c in await list_connections():
        if c.get('id') == machine_id and kind(c):
            return c
    raise MachineError('Unknown machine.')


async def save_machine(entry: dict):
    connections = [c for c in await list_connections() if c.get('id') != entry['id']]
    await Config.upsert({CONNECTIONS: [*connections, entry]})


async def update_state(machine_id: str, **fields):
    connections = await list_connections()
    for c in connections:
        if c.get('id') == machine_id and kind(c):
            c[kind(c)] = {**state(c), **fields}
    await Config.upsert({CONNECTIONS: connections})


async def open_host(machine: dict):
    """Where the machine's scripts run: this computer, or over SSH."""
    if kind(machine) == 'local':
        return local.LocalHost()
    return ssh.SSHHost(machine['ssh'], await ssh.machine_key(machine['id']))


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


async def run_bootstrap(
    host,
    machine_id: str,
    api_key: str,
    on_step,
    version: str = 'latest',
    start_dir: str = '',
    flags: str = '',
    install: str = '',
) -> tuple[str, str, str | None]:
    """Install or upgrade Open Terminal and start it. Returns (install root, installed version, warning).

    `install` (see install_args) also runs `open-terminal install-deps`. When that fails the
    machine is still set up, with a warning.
    """
    settings = {'START_DIR': start_dir, 'FLAGS': flags, 'DEPS': install}
    script = ''.join(f'{name}={shlex.quote(value)}\n' for name, value in settings.items()) + render(
        BOOTSTRAP,
        ID=machine_id,
        VERSION=requested_version(version),
        MIN_VERSION=MIN_OPEN_TERMINAL_VERSION,
        UV_VERSION=UV_VERSION,
        API_KEY=api_key,
    )
    proc = await host.start(script)  # stdin, not argv: the API key never shows up in `ps`
    root, installed, error, warning, tail = None, None, None, None, deque(maxlen=80)
    try:
        # A cold install downloads Python and the package; system packages can be far larger.
        async with asyncio.timeout(2700 if install else 900):
            async for line in proc.lines():
                line = line.rstrip('\n')
                tail.append(line)
                if not line.startswith('OPEN_WEBUI:'):
                    continue
                _, name, value = line.split(':', 2)
                if name == 'step':
                    await on_step(value)
                elif name == 'root':
                    root = value
                elif name == 'version':
                    installed = value
                elif name == 'error':
                    error = value
                elif name == 'warning':
                    warning = value
            status = await proc.wait()
    finally:
        proc.close()
    if status != 0 or not root:
        raise MachineError(error or '\n'.join(tail) or 'Setup failed.')
    if not host.valid_root(root, machine_id):
        raise MachineError(f'Unexpected install path: {root}')
    if warning:
        warning = (
            f'Packages were not installed: {warning}\n'
            f'Run this on the machine, then restart it here: {root}/bin/open-terminal install-deps {install}'
        )
    return root, installed or '', warning


# ---------------------------------------------------------------------------
# Connections (opened lazily, one per machine per worker process)
# ---------------------------------------------------------------------------


async def _wait_healthy(path: str, seconds: float = 60):
    async with aiohttp.ClientSession(connector=aiohttp.UnixConnector(path=path)) as session:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            with suppress(aiohttp.ClientError, asyncio.TimeoutError):
                async with session.get('http://machine/health', timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        return
            await asyncio.sleep(0.5)
    raise MachineError('Open Terminal did not become healthy within a minute.')


class Tunnel:
    """The socket Open WebUI talks to: the local end of an SSH tunnel, or (conn None) Open Terminal's own socket."""

    def __init__(self, conn, path: str, server=None):
        self.conn, self.path, self.server = conn, path, server

    @property
    def alive(self) -> bool:
        if self.conn is None:
            return Path(self.path).exists()
        return not self.conn.is_closed()

    def close(self):
        if self.conn is None:
            return  # Open Terminal's own socket: never delete it
        if self.server:
            self.server.close()
        self.conn.close()
        Path(self.path).unlink(missing_ok=True)


class Tunnels:
    def __init__(self):
        self.open: dict[str, Tunnel] = {}
        self.opening: dict[str, asyncio.Task] = {}

    async def socket_for(self, machine_id: str) -> str:
        tunnel = self.open.get(machine_id)
        if tunnel and tunnel.alive:
            return tunnel.path
        task = self.opening.get(machine_id)
        if task is None:
            task = asyncio.create_task(self._replace(machine_id))
            self.opening[machine_id] = task
            task.add_done_callback(partial(self._opened, machine_id))
        # Shielded: a caller with a short timeout gives up waiting without aborting the open for everyone.
        return await asyncio.shield(task)

    def _opened(self, machine_id: str, task: asyncio.Task):
        if self.opening.get(machine_id) is task:
            del self.opening[machine_id]
        if not task.cancelled():
            task.exception()  # mark retrieved: an open nobody waited for must not log "never retrieved"

    async def _replace(self, machine_id: str) -> str:
        old = self.open.pop(machine_id, None)
        if old:
            old.close()
        tunnel = await self._open(await get_machine(machine_id))
        self.open[machine_id] = tunnel
        return tunnel.path

    async def _open(self, machine: dict) -> Tunnel:
        root = state(machine)['root']
        if kind(machine) == 'local':
            await local.LocalHost().sh(f'{shlex.quote(root + "/start.sh")}\n')  # relaunch after a restart or crash
            path = f'{root}/run/api.sock'
            await _wait_healthy(path)
            return Tunnel(None, path)
        path = str(RUN_DIR / f'{machine["id"]}.sock')
        Path(path).unlink(missing_ok=True)  # a stale file from a dropped tunnel blocks listening
        conn, server = await ssh.open_tunnel(machine, path)
        tunnel = Tunnel(conn, path, server)
        try:
            await _wait_healthy(path)
        except BaseException:
            tunnel.close()
            raise
        return tunnel

    async def drop(self, machine_id: str):
        task = self.opening.pop(machine_id, None)
        if task:
            task.cancel()
            await asyncio.wait([task])
        tunnel = self.open.pop(machine_id, None)
        if tunnel:
            tunnel.close()


tunnels = Tunnels()


# ---------------------------------------------------------------------------
# Client used by get_machine_client('ssh://<id>' or 'local://<id>')
# ---------------------------------------------------------------------------


class _Operation:
    """Supports `await op` and `async with op`, like aiohttp's own request objects."""

    def __init__(self, coroutine):
        self.coroutine, self.value = coroutine, None

    def __await__(self):
        return self.coroutine.__await__()

    async def __aenter__(self):
        self.value = await self.coroutine
        return self.value

    async def __aexit__(self, *_):
        if isinstance(self.value, aiohttp.ClientWebSocketResponse):
            await self.value.close()
        elif self.value is not None:
            self.value.release()


class MachineClient:
    def __init__(self, machine_id: str, **kwargs):
        kwargs.pop('trust_env', None)  # HTTP_PROXY must never apply to a local socket
        self.machine_id, self.kwargs = machine_id, kwargs
        self.session: aiohttp.ClientSession | None = None
        self.path: str | None = None

    async def _session(self) -> aiohttp.ClientSession:
        # Opening the connection counts against the caller's timeout, like a TCP connect would.
        timeout = self.kwargs.get('timeout')
        limit = getattr(timeout, 'total', None) or getattr(timeout, 'connect', None)
        try:
            async with asyncio.timeout(limit):
                path = await tunnels.socket_for(self.machine_id)
        except TimeoutError:
            raise
        except Exception as error:
            # Callers already handle aiohttp connection errors for unreachable servers.
            raise aiohttp.ClientConnectionError(f'Machine unavailable: {describe(error)}') from error
        if self.session is None or self.session.closed or path != self.path:
            await self._reset()
            self.session = aiohttp.ClientSession(connector=aiohttp.UnixConnector(path=path), **self.kwargs)
            self.path = path
        return self.session

    async def _reset(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = self.path = None

    @staticmethod
    def _url(url) -> str:
        parts = urlsplit(str(url))
        return f'http://machine{parts.path or "/"}' + (f'?{parts.query}' if parts.query else '')

    async def _request(self, method: str, url, **kwargs):
        replayable = method in SAFE_METHODS and kwargs.get('data') is None
        for attempt in (0, 1):
            session = await self._session()
            try:
                return await session.request(method, self._url(url), **kwargs)
            except aiohttp.ClientConnectionError as error:
                # Reconnect once (which also restarts Open Terminal if it died). Always safe when
                # the connect itself failed, since nothing was sent; otherwise only for safe requests.
                if attempt or not (replayable or isinstance(error, aiohttp.ClientConnectorError)):
                    raise
                await self._reset()
                await tunnels.drop(self.machine_id)

    async def _ws_connect(self, url, **kwargs):
        kwargs.pop('ssl', None)
        for attempt in (0, 1):
            session = await self._session()
            try:
                return await session.ws_connect(self._url(url), **kwargs)
            except aiohttp.ClientConnectorError:
                if attempt:
                    raise
                await self._reset()
                await tunnels.drop(self.machine_id)

    def request(self, method, url, **kwargs):
        return _Operation(self._request(method.upper(), url, **kwargs))

    def ws_connect(self, url, **kwargs):
        return _Operation(self._ws_connect(url, **kwargs))

    def __getattr__(self, name):
        if name in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
            return lambda url, **kwargs: self.request(name.upper(), url, **kwargs)
        raise AttributeError(name)

    @property
    def closed(self) -> bool:
        return self.session is None or self.session.closed

    async def close(self):
        await self._reset()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def emit_step(admin_id: str, machine_id: str, value: str, **extra):
    """Tell the admin's browser how far a machine's setup is (`machines:progress`)."""
    from open_webui.socket.main import emit_to_users

    await emit_to_users(
        'events',
        {'data': {'type': 'machines:progress', 'id': machine_id, 'step': value, **extra}},
        [admin_id],
    )


async def provision(
    request,
    machine_id: str,
    admin_id: str,
    *,
    name: str | None = None,
    target: dict | None = None,
    is_local: bool = False,
    version: str | None = None,
    start_dir: str | None = None,
    flags: str | None = None,
    deps: list[str] | None = None,
    packages: list[str] | None = None,
):
    """Create (target given, or is_local) or upgrade/repair (neither) a machine, streaming progress to the admin.

    `version` is 'latest' or an exact Open Terminal version, `start_dir` is where sessions start,
    `flags` are extra `open-terminal run` flags (see clean_flags), and `deps` and `packages` are
    what `open-terminal install-deps` adds (see install_args).
    When omitted, the machine keeps what the admin chose last time.
    """
    from open_webui.utils.machines import notify_machines_changed
    from open_webui.utils.tools import set_machines

    step = partial(emit_step, admin_id, machine_id)
    existing = None
    with suppress(MachineError):
        existing = await get_machine(machine_id)
    if existing:
        is_local = kind(existing) == 'local'
    elif not is_local and not target:
        raise MachineError('Unknown machine.')
    current = state(existing) if existing else {}
    source = current if existing else (target or {})
    api_key = (existing or {}).get('key') or secrets.token_urlsafe(32)
    requested = requested_version(version if version is not None else current.get('requested_version'))
    if start_dir is None:
        start_dir = current.get('start_dir') or ''
    if is_local and not start_dir:
        start_dir = local.default_start_dir()
    if flags is None:
        flags = current.get('flags') or ''
    if deps is None:
        deps = current.get('deps') or []
    if packages is None:
        packages = current.get('packages') or []

    try:
        if existing:
            await update_state(machine_id, status='installing')
            await tunnels.drop(machine_id)
        await step('connect')
        machine = existing or ({'id': machine_id, 'local': {}} if is_local else {'id': machine_id, 'ssh': target})
        async with await open_host(machine) as host:
            root, installed, warning = await run_bootstrap(
                host, machine_id, api_key, step, requested, start_dir, flags, install_args(deps, packages)
            )
            transport = await host.transport(root)

        entry = existing or {
            'id': machine_id,
            'name': name or ('Local' if is_local else target['host']),
            'url': f'{"local" if is_local else "ssh"}://{machine_id}',
            'auth_type': 'bearer',
            'enabled': True,
            'config': {'access_grants': []},  # admins only until shared
        }
        entry['key'] = api_key
        entry['local' if is_local else 'ssh'] = {
            **({} if is_local else {k: source[k] for k in ('host', 'port', 'username', 'host_key')}),
            'root': root,
            'start_dir': start_dir,
            'flags': flags,
            'version': installed,
            'requested_version': requested,
            'deps': deps,
            'packages': packages,
            'transport': transport,
            'status': 'ready',
            'error': None,
            'warning': warning,
        }
        await save_machine(entry)
        if not is_local:
            await ssh.attach_secret(machine_id)

        await step('health')
        await tunnels.socket_for(machine_id)
        await set_machines(request)  # load its OpenAPI spec like any other machine
        await notify_machines_changed([admin_id])
        await step('ready', message=warning)
    except Exception as error:
        log.exception('Provisioning %s failed', machine_id)
        message = describe(error)
        if existing:
            await update_state(machine_id, status='error', error=message)
        await step('error', message=message)


async def configure(machine_id: str, start_dir: str, flags: str):
    """Change where sessions start and the `open-terminal run` flags, then restart Open Terminal with them."""
    machine = await get_machine(machine_id)
    current = state(machine)
    start_dir = clean_start_dir(start_dir) or (local.default_start_dir() if kind(machine) == 'local' else '')
    flags = clean_flags(flags)

    async def on_step(_):
        pass

    # The installed version, so this does not upgrade. Also brings older installs' start.sh up to date.
    apply = partial(run_bootstrap, version=current.get('version'))
    await tunnels.drop(machine_id)
    async with await open_host(machine) as host:
        try:
            await apply(host, machine_id, machine['key'], on_step, start_dir=start_dir, flags=flags)
        except MachineError:  # a wrong flag keeps Open Terminal from starting: go back to what worked
            with suppress(Exception):
                await apply(
                    host,
                    machine_id,
                    machine['key'],
                    on_step,
                    start_dir=current.get('start_dir') or '',
                    flags=current.get('flags') or '',
                )
            raise
    await update_state(machine_id, start_dir=start_dir, flags=flags)


async def install(request, machine_id: str, admin_id: str, deps: list[str], packages: list[str]):
    """Run `open-terminal install-deps` on a machine that is already set up, streaming progress to the admin."""
    from open_webui.utils.tools import set_machines

    step = partial(emit_step, admin_id, machine_id)
    try:
        args = install_args(deps, packages)
        machine = await get_machine(machine_id)
        binary = f'{state(machine)["root"]}/bin/open-terminal'
        await step('packages')
        async with await open_host(machine) as host:
            try:
                # stdin is the script, so sudo must not read a password from it.
                output = await host.sh(f'{shlex.quote(binary)} install-deps --yes {args} </dev/null\n', timeout=2700)
            except MachineError as error:
                hint = f'To install by hand, run this on the machine: {binary} install-deps {args}'
                raise MachineError(f'{error}\n{hint}') from error
        await update_state(machine_id, deps=deps, packages=packages, warning=None)
        if 'Will run:' in output:  # something was installed: restart so the server offers it
            await restart(machine_id)
            await set_machines(request)
        await step('ready', output=output.strip()[-2000:])
    except Exception as error:
        log.exception('Installing packages on %s failed', machine_id)
        await step('error', message=describe(error))


async def restart(machine_id: str):
    machine = await get_machine(machine_id)
    root = state(machine)['root']
    await tunnels.drop(machine_id)
    async with await open_host(machine) as host:
        await host.sh(f'{shlex.quote(root + "/stop.sh")}\n{shlex.quote(root + "/start.sh")}\n')
    await tunnels.socket_for(machine_id)


async def logs(machine_id: str, lines: int = 200) -> str:
    machine = await get_machine(machine_id)
    root = state(machine)['root']
    async with await open_host(machine) as host:
        return await host.sh(f'tail -n {int(lines)} {shlex.quote(root + "/server.log")} 2>/dev/null || true\n')


async def forget(machine_id: str):
    """Drop our own state (connection + key). Leaves the install in place."""
    await tunnels.drop(machine_id)
    await ssh.delete_secret(machine_id)


async def uninstall(machine_id: str):
    """Stop the server, delete the install, remove the machine and its key."""
    machine = await get_machine(machine_id)
    root = state(machine)['root']
    await tunnels.drop(machine_id)
    async with await open_host(machine) as host:
        # rmdir only succeeds when the parent folder is empty, so other installs there are kept.
        parent = shlex.quote(root.rsplit('/', 1)[0])
        await host.sh(
            f'{shlex.quote(root + "/stop.sh")} || true\nrm -rf {shlex.quote(root)}\nrmdir {parent} 2>/dev/null || true\n',
        )
    await remove(machine_id)


async def remove(machine_id: str):
    """Remove the machine from Open WebUI only (for machines that are gone or unreachable)."""
    await Config.upsert({CONNECTIONS: [c for c in await list_connections() if c.get('id') != machine_id]})
    await forget(machine_id)
