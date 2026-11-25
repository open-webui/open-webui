"""SSH machines: keys, host-key pinning, running scripts and opening tunnels over SSH.

An admin authorizes a key Open WebUI generated. managed.py installs Open Terminal under
~/.open-webui/<id> on the host through SSHHost, and reaches its Unix socket through
open_tunnel (sshd's streamlocal forwarding, or `open-terminal bridge` over exec).
"""

import asyncio
import base64
import re
import secrets
import shlex
import time
from functools import partial

import asyncssh
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.models.config import Config
from open_webui.utils.machines import MachineError

SECRETS = 'machines.secrets'  # never returned to the browser
PENDING_TTL = 3600  # keypairs never attached to a machine are pruned after an hour
ROOT_RE = re.compile(r'/[A-Za-z0-9._/@+-]+/\.open-webui/m_[0-9a-f]{8}')

# Run scripts under the user's login shell so profile PATH applies (claude, codex, nvm, ...).
LOGIN = (
    """sh -c 'case "$SHELL" in """
    """*/bash|*/zsh|*/ksh|*/fish) exec "$SHELL" -l -c "exec sh -s";; *) exec sh -s;; esac'"""
)

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


async def machine_key(machine_id: str) -> asyncssh.SSHKey:
    entry = (await _load_secrets()).get(machine_id)
    if not entry:
        raise MachineError('No key is stored for this machine.')
    return asyncssh.import_private_key(_cipher().decrypt(entry['private_key'].encode()))


async def attach_secret(machine_id: str):
    store = await _load_secrets()
    if machine_id in store:
        store[machine_id]['attached'] = True
        await Config.upsert({SECRETS: store})


async def delete_secret(machine_id: str):
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
    async with await connect(ssh, key=await machine_key(machine_id)):
        pass


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


class _Process:
    def __init__(self, proc):
        self.proc = proc

    async def lines(self):
        async for line in self.proc.stdout:
            yield line

    async def wait(self) -> int:
        await self.proc.wait()
        return self.proc.exit_status

    def close(self):
        self.proc.close()


class SSHHost:
    """Runs a machine's scripts over SSH (see managed.open_host)."""

    def __init__(self, target: dict, key: asyncssh.SSHKey):
        self.target, self.key = target, key

    async def __aenter__(self):
        self.conn = await connect(self.target, key=self.key)
        return self

    async def __aexit__(self, *_):
        self.conn.close()
        await self.conn.wait_closed()

    async def start(self, script: str) -> _Process:
        proc = await self.conn.create_process(LOGIN, stderr=asyncssh.STDOUT)
        proc.stdin.write(script)
        proc.stdin.write_eof()
        return _Process(proc)

    async def sh(self, script: str, *, timeout: float = 60) -> str:
        return await sh(self.conn, script, timeout=timeout)

    def valid_root(self, root: str, machine_id: str) -> bool:
        return bool(ROOT_RE.fullmatch(root)) and root.endswith('/' + machine_id)

    async def transport(self, root: str) -> str:
        return await detect_transport(self.conn, root)


async def open_tunnel(machine: dict, path: str):
    """Make sure Open Terminal runs, then expose its socket at `path` here. Returns (conn, server)."""
    target = machine['ssh']
    root = target['root']
    conn = await connect(target, key=await machine_key(machine['id']))
    try:
        await sh(conn, f'{shlex.quote(root + "/start.sh")}\n')  # relaunch after a reboot or crash
        server = None
        if target.get('transport') == 'stdio':
            server = await asyncio.start_unix_server(partial(_bridge, conn, root), path=path)
        else:
            await conn.forward_local_path(path, f'{root}/run/api.sock')
        return conn, server
    except BaseException:
        conn.close()
        raise
