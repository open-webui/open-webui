"""SSH-provisioned Open Terminal machines.

An admin authorizes a key Open WebUI generated. We install Open Terminal under
~/.open-webui/<id> on the host, run it on a Unix socket (no TCP port), and
reach it through SSH channels. The machine then lives in machines.connections
with url ssh://<id>, so every existing machine feature works unchanged.
"""

import asyncio
import base64
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
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.models.config import Config

log = logging.getLogger(__name__)

# Machines install the latest Open Terminal by default, or a version the admin pins.
# This is the oldest one Open WebUI works with (first with `open-terminal bridge`).
MIN_OPEN_TERMINAL_VERSION = '0.17.21'
UV_VERSION = '0.13.9'
CONNECTIONS = 'machines.connections'
SECRETS = 'machines.secrets'  # never returned to the browser
PENDING_TTL = 3600  # keypairs never attached to a machine are pruned after an hour
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}

ID_RE = re.compile(r'm_[0-9a-f]{8}')
ROOT_RE = re.compile(r'/[A-Za-z0-9._/@+-]+/\.open-webui/m_[0-9a-f]{8}')
TOKENS = {
    'ID': ID_RE,
    'VERSION': re.compile(r'latest|\d+\.\d+\.\d+'),
    'MIN_VERSION': re.compile(r'\d+\.\d+\.\d+'),
    'UV_VERSION': re.compile(r'\d+\.\d+\.\d+'),
    'API_KEY': re.compile(r'[A-Za-z0-9_-]{32,64}'),
}

# Run scripts under the user's login shell so profile PATH applies (claude, codex, nvm, ...).
LOGIN = (
    """sh -c 'case "$SHELL" in """
    """*/bash|*/zsh|*/ksh|*/fish) exec "$SHELL" -l -c "exec sh -s";; *) exec sh -s;; esac'"""
)
BOOTSTRAP = Path(__file__).with_name('bootstrap.sh').read_text()

# Unix socket paths max out around 104 characters on macOS, so keep this short.
RUN_DIR = Path(tempfile.mkdtemp(prefix='open-webui-', dir='/tmp'))


class MachineError(Exception):
    pass


def describe(error: BaseException) -> str:
    """Turn SSH failures into something an admin can act on."""
    if isinstance(error, asyncssh.HostKeyNotVerifiable):
        return "The machine's host key changed. Remove and re-add the machine if this is expected."
    if isinstance(error, asyncssh.PermissionDenied):
        return 'SSH login was refused. Check that the key is in ~/.ssh/authorized_keys, or the password is right.'
    if isinstance(error, asyncio.TimeoutError):
        return 'The machine took too long to respond.'
    if isinstance(error, OSError):
        return f'Could not reach the machine: {error.strerror or error}'
    return str(error) or type(error).__name__


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------


def _cipher() -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'open-webui/machine-secrets/v1').derive(
        WEBUI_SECRET_KEY.encode()
    )
    return Fernet(base64.urlsafe_b64encode(key))


async def _load_secrets() -> dict:
    return dict(await Config.get(SECRETS, {}) or {})


async def new_keypair() -> tuple[str, str]:
    """Create a machine id and an ed25519 key for it. Returns (id, public key line)."""
    machine_id = f'm_{secrets.token_hex(4)}'
    key = asyncssh.generate_private_key('ssh-ed25519', comment=f'open-webui-{machine_id}')
    now = int(time.time())
    store = {
        k: v for k, v in (await _load_secrets()).items() if v.get('attached') or now - v['created_at'] < PENDING_TTL
    }
    store[machine_id] = {
        'private_key': _cipher().encrypt(key.export_private_key()).decode(),
        'created_at': now,
        'attached': False,
    }
    await Config.upsert({SECRETS: store})
    return machine_id, key.export_public_key().decode().strip()


async def _private_key(machine_id: str) -> asyncssh.SSHKey:
    entry = (await _load_secrets()).get(machine_id)
    if not entry:
        raise MachineError('No key is stored for this machine.')
    return asyncssh.import_private_key(_cipher().decrypt(entry['private_key'].encode()))


async def _attach_secret(machine_id: str):
    store = await _load_secrets()
    if machine_id in store:
        store[machine_id]['attached'] = True
        await Config.upsert({SECRETS: store})


async def _delete_secret(machine_id: str):
    store = await _load_secrets()
    if store.pop(machine_id, None) is not None:
        await Config.upsert({SECRETS: store})


# ---------------------------------------------------------------------------
# SSH
# ---------------------------------------------------------------------------


def _known_hosts(ssh: dict) -> asyncssh.SSHKnownHosts:
    pattern = ssh['host'] if ssh['port'] == 22 else f'[{ssh["host"]}]:{ssh["port"]}'
    return asyncssh.import_known_hosts(f'{pattern} {ssh["host_key"]}\n')


async def probe_host_key(host: str, port: int) -> tuple[str, str]:
    """Fetch the host key without logging in. Returns (public key line, SHA256 fingerprint)."""
    key = await asyncio.wait_for(asyncssh.get_server_host_key(host, port), 15)
    if key is None:
        raise MachineError('The server did not present a host key.')
    return key.export_public_key().decode().strip(), key.get_fingerprint()


async def connect(ssh: dict, *, key: asyncssh.SSHKey | None = None, password: str | None = None):
    return await asyncssh.connect(
        ssh['host'],
        port=ssh['port'],
        username=ssh['username'],
        known_hosts=_known_hosts(ssh),
        client_keys=[key] if key else None,
        password=password,
        agent_path=None,  # never use an ssh-agent on the Open WebUI host
        config=None,  # never read ~/.ssh/config on the Open WebUI host
        preferred_auth='publickey' if key else 'keyboard-interactive,password',
        keepalive_interval=15,
        keepalive_count_max=3,
        connect_timeout=10,
    )


async def sh(conn, script: str, *, timeout: float = 60) -> str:
    """Run a POSIX script on the machine under the user's login shell."""
    res = await asyncio.wait_for(conn.run(LOGIN, input=script, check=False), timeout)
    if res.exit_status != 0:
        detail = (res.stderr or res.stdout or '').strip()[-2000:]
        raise MachineError(detail or f'Remote command failed with exit code {res.exit_status}.')
    return res.stdout


async def install_public_key(
    ssh: dict,
    machine_id: str,
    public_key: str,
    *,
    password: str = '',
    private_key: str = '',
    passphrase: str = '',
):
    """Log in once with a password or a key the machine already trusts, add our key, and prove it works.

    The password or private key is only used for this login and is never stored.
    """
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+ open-webui-m_[0-9a-f]{8}', public_key):
        raise MachineError('Invalid public key.')
    if private_key:
        try:
            login_key = asyncssh.import_private_key(private_key, passphrase or None)
        except asyncssh.KeyEncryptionError as error:
            raise MachineError('The passphrase for this private key is wrong.') from error
        except asyncssh.KeyImportError as error:
            if 'assphrase' in str(error):
                raise MachineError('This private key needs its passphrase.') from error
            raise MachineError('That private key could not be read.') from error
        refused = 'The machine did not accept this private key.'
    elif password:
        login_key = None
        refused = 'The password was refused, or this machine only allows key login.'
    else:
        raise MachineError('Enter a password or a private key.')
    try:
        conn = await connect(ssh, key=login_key, password=None if login_key else password)
    except asyncssh.PermissionDenied as error:
        raise MachineError(refused) from error
    async with conn:
        await sh(
            conn,
            'umask 077; mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && '
            f"(grep -qxF '{public_key}' ~/.ssh/authorized_keys || "
            f"printf '%s\\n' '{public_key}' >> ~/.ssh/authorized_keys)",
        )
    async with await connect(ssh, key=await _private_key(machine_id)):
        pass


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


def render(template: str, **values: str) -> str:
    for name, value in values.items():
        if not TOKENS[name].fullmatch(value):
            raise MachineError(f'Refusing to render {name}.')
    return re.sub(r'__OPEN_WEBUI_([A-Z_]+)__', lambda m: values[m.group(1)], template)


async def run_bootstrap(conn, machine_id: str, api_key: str, on_step, version: str = 'latest') -> tuple[str, str]:
    """Install or upgrade Open Terminal and start it. Returns (install root, installed version)."""
    script = render(
        BOOTSTRAP,
        ID=machine_id,
        VERSION=requested_version(version),
        MIN_VERSION=MIN_OPEN_TERMINAL_VERSION,
        UV_VERSION=UV_VERSION,
        API_KEY=api_key,
    )
    proc = await conn.create_process(LOGIN, stderr=asyncssh.STDOUT)
    proc.stdin.write(script)  # stdin, not argv: the API key never shows up in `ps`
    proc.stdin.write_eof()
    root, installed, error, tail = None, None, None, deque(maxlen=80)
    try:
        async with asyncio.timeout(900):  # a cold install downloads Python and the package
            async for line in proc.stdout:
                line = line.rstrip('\n')
                tail.append(line)
                if not line.startswith('OPEN_WEBUI:'):
                    continue
                _, kind, value = line.split(':', 2)
                if kind == 'step':
                    await on_step(value)
                elif kind == 'root':
                    root = value
                elif kind == 'version':
                    installed = value
                elif kind == 'error':
                    error = value
            await proc.wait()
    finally:
        proc.close()
    if proc.exit_status != 0 or not root:
        raise MachineError(error or '\n'.join(tail) or 'Setup failed.')
    if not ROOT_RE.fullmatch(root):
        raise MachineError(f'Unexpected install path: {root}')
    return root, installed or ''


async def detect_transport(conn, root: str) -> str:
    """'streamlocal' if sshd forwards to Unix sockets, else 'stdio' (`open-terminal bridge` over exec)."""
    try:
        _, writer = await conn.open_unix_connection(f'{root}/run/api.sock')
        writer.close()
        return 'streamlocal'
    except asyncssh.ChannelOpenError as error:
        # OpenSSH answers "forbidden" and "nothing listening" with the same code, so ask the box.
        listening = await conn.run(f'test -S {shlex.quote(root + "/run/api.sock")}')
        if listening.exit_status == 0:
            return 'stdio'  # socket is there, the forward was refused: AllowStreamLocalForwarding no
        raise MachineError('Open Terminal is not listening on the machine.') from error


# ---------------------------------------------------------------------------
# Stored machines
# ---------------------------------------------------------------------------


async def list_connections() -> list[dict]:
    return list(await Config.get(CONNECTIONS, []) or [])


async def get_machine(machine_id: str) -> dict:
    for c in await list_connections():
        if c.get('id') == machine_id and c.get('ssh'):
            return c
    raise MachineError('Unknown machine.')


async def save_machine(entry: dict):
    connections = [c for c in await list_connections() if c.get('id') != entry['id']]
    await Config.upsert({CONNECTIONS: [*connections, entry]})


async def update_ssh(machine_id: str, **fields):
    connections = await list_connections()
    for c in connections:
        if c.get('id') == machine_id and c.get('ssh'):
            c['ssh'] = {**c['ssh'], **fields}
    await Config.upsert({CONNECTIONS: connections})


# ---------------------------------------------------------------------------
# Tunnels (one SSH connection per machine per worker process)
# ---------------------------------------------------------------------------


async def _bridge(conn, root: str, reader, writer):
    """stdio transport: each local connection gets its own `open-terminal bridge` on the machine."""
    proc = await conn.create_process(
        f'{shlex.quote(root + "/bin/open-terminal")} bridge {shlex.quote(root + "/run/api.sock")}', encoding=None
    )

    async def up():
        while data := await reader.read(65536):
            proc.stdin.write(data)
        proc.stdin.write_eof()

    async def down():
        while data := await proc.stdout.read(65536):
            writer.write(data)
            await writer.drain()

    try:
        await asyncio.gather(up(), down(), return_exceptions=True)
    finally:
        proc.close()
        writer.close()


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
    def __init__(self, conn, path: str, server=None):
        self.conn, self.path, self.server = conn, path, server

    @property
    def alive(self) -> bool:
        return not self.conn.is_closed()

    def close(self):
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
        ssh = machine['ssh']
        root = ssh['root']
        conn = await connect(ssh, key=await _private_key(machine['id']))
        try:
            await sh(conn, f'{shlex.quote(root + "/start.sh")}\n')  # relaunch after a reboot or crash
            path = str(RUN_DIR / f'{machine["id"]}.sock')
            Path(path).unlink(missing_ok=True)  # a stale file from a dropped tunnel blocks listening
            server = None
            if ssh.get('transport') == 'stdio':
                server = await asyncio.start_unix_server(partial(_bridge, conn, root), path=path)
            else:
                await conn.forward_local_path(path, f'{root}/run/api.sock')
            await _wait_healthy(path)
            return Tunnel(conn, path, server)
        except BaseException:
            conn.close()
            raise

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
# Client used by get_machine_client('ssh://<id>')
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
        # Opening the tunnel counts against the caller's timeout, like a TCP connect would.
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
            except aiohttp.ClientConnectionError:
                # The SSH connection dropped before a response: reconnect once for safe requests.
                if attempt or not replayable:
                    raise
                await self._reset()
                await tunnels.drop(self.machine_id)

    async def _ws_connect(self, url, **kwargs):
        kwargs.pop('ssl', None)
        session = await self._session()
        return await session.ws_connect(self._url(url), **kwargs)

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


async def provision(
    request,
    machine_id: str,
    admin_id: str,
    *,
    name: str | None = None,
    ssh: dict | None = None,
    version: str | None = None,
):
    """Create (ssh given) or upgrade/repair (ssh omitted) a machine, streaming progress to the admin.

    `version` is 'latest' or an exact Open Terminal version. When omitted, the machine keeps
    the version the admin chose last time ('latest' if none).
    """
    from open_webui.socket.main import emit_to_users
    from open_webui.utils.machines import notify_machines_changed
    from open_webui.utils.tools import set_terminal_servers

    async def step(value: str, **extra):
        await emit_to_users(
            'events',
            {'data': {'type': 'machines:progress', 'id': machine_id, 'step': value, **extra}},
            [admin_id],
        )

    existing = None
    with suppress(MachineError):
        existing = await get_machine(machine_id)
    ssh = ssh or (existing or {}).get('ssh')
    if not ssh:
        raise MachineError('Unknown machine.')
    api_key = (existing or {}).get('key') or secrets.token_urlsafe(32)
    requested = requested_version(version if version is not None else ssh.get('requested_version'))

    try:
        if existing:
            await update_ssh(machine_id, status='installing')
            await tunnels.drop(machine_id)
        await step('connect')
        async with await connect(ssh, key=await _private_key(machine_id)) as conn:
            root, installed = await run_bootstrap(conn, machine_id, api_key, step, requested)
            transport = await detect_transport(conn, root)

        entry = existing or {
            'id': machine_id,
            'name': name or ssh['host'],
            'url': f'ssh://{machine_id}',
            'auth_type': 'bearer',
            'enabled': True,
            'config': {'access_grants': []},
        }
        entry['key'] = api_key
        entry['ssh'] = {
            **{k: ssh[k] for k in ('host', 'port', 'username', 'host_key')},
            'root': root,
            'version': installed,
            'requested_version': requested,
            'transport': transport,
            'status': 'ready',
            'error': None,
        }
        await save_machine(entry)
        await _attach_secret(machine_id)

        await step('health')
        await tunnels.socket_for(machine_id)
        await set_terminal_servers(request)  # load its OpenAPI spec like any other terminal
        await notify_machines_changed([admin_id])
        await step('ready')
    except Exception as error:
        log.exception('Provisioning %s failed', machine_id)
        message = describe(error)
        if existing:
            await update_ssh(machine_id, status='error', error=message)
        await step('error', message=message)


async def restart(machine_id: str):
    machine = await get_machine(machine_id)
    root = machine['ssh']['root']
    await tunnels.drop(machine_id)
    async with await connect(machine['ssh'], key=await _private_key(machine_id)) as conn:
        await sh(conn, f'{shlex.quote(root + "/stop.sh")}\n{shlex.quote(root + "/start.sh")}\n')
    await tunnels.socket_for(machine_id)


async def logs(machine_id: str, lines: int = 200) -> str:
    machine = await get_machine(machine_id)
    root = machine['ssh']['root']
    async with await connect(machine['ssh'], key=await _private_key(machine_id)) as conn:
        return await sh(conn, f'tail -n {int(lines)} {shlex.quote(root + "/server.log")} 2>/dev/null || true\n')


async def forget(machine_id: str):
    """Drop our local state (tunnel + key). Leaves the install on the machine."""
    await tunnels.drop(machine_id)
    await _delete_secret(machine_id)


async def uninstall(machine_id: str):
    """Stop the server, delete the install, remove the machine and its key."""
    machine = await get_machine(machine_id)
    root = machine['ssh']['root']
    await tunnels.drop(machine_id)
    async with await connect(machine['ssh'], key=await _private_key(machine_id)) as conn:
        # rmdir only succeeds when ~/.open-webui is empty, so other installs there are kept.
        parent = shlex.quote(root.rsplit('/', 1)[0])
        await sh(
            conn,
            f'{shlex.quote(root + "/stop.sh")} || true\nrm -rf {shlex.quote(root)}\nrmdir {parent} 2>/dev/null || true\n',
        )
    await remove(machine_id)


async def remove(machine_id: str):
    """Remove the machine from Open WebUI only (for machines that are gone or unreachable)."""
    await Config.upsert({CONNECTIONS: [c for c in await list_connections() if c.get('id') != machine_id]})
    await forget(machine_id)
