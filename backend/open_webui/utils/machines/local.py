"""Local machines: Open Terminal on the server Open WebUI runs on (experimental, opt-in).

Like Open WebUI Computer, it serves the machine it runs on and starts in your project
folder. It only makes sense for a single Open WebUI instance.

The install lives in ~/.open-webui/<id>, like SSH machines. In Docker, home is wiped when
the container is recreated, so it lives in the data volume instead.
"""

import asyncio
import os
import signal
from contextlib import suppress
from pathlib import Path

from open_webui.env import DATA_DIR, DOCKER
from open_webui.utils.machines import MachineError

# Not the data folder outside Docker: pip installs keep it deep in site-packages, past the
# ~104-byte limit for Unix socket paths.
BASE = Path(DATA_DIR).resolve() / 'machines' if DOCKER else Path.home() / '.open-webui'

# Only what Open Terminal needs. Open WebUI's own settings (WEBUI_SECRET_KEY, DATABASE_URL,
# OAuth secrets, ...) are not passed down to it.
ENV = {
    'HOME': os.environ.get('HOME') or '/root',
    'PATH': os.environ.get('PATH') or '/usr/local/bin:/usr/bin:/bin',
    'LANG': os.environ.get('LANG') or 'C.UTF-8',
    'OPEN_WEBUI_MACHINES_DIR': str(BASE),
}


def root_for(machine_id: str) -> str:
    root = str(BASE / machine_id)
    if len(root + '/run/api.sock') > 100:  # Unix socket paths are capped around 104 bytes
        raise MachineError(f'This path is too long for a Unix socket: {BASE}')
    return root


def default_folder() -> str:
    """Where sessions start, like Open WebUI Computer: your project, not Open WebUI's own files."""
    if Path('/workspace').is_dir():
        return '/workspace'  # the Docker docs mount the project here
    if DOCKER:
        path = Path(DATA_DIR).resolve() / 'workspace'  # kept across image updates
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    return os.getcwd()  # the folder Open WebUI was started from


class _Process:
    def __init__(self, proc: asyncio.subprocess.Process):
        self.proc = proc

    async def lines(self):
        async for line in self.proc.stdout:
            yield line.decode(errors='replace')

    async def wait(self) -> int:
        return await self.proc.wait()

    def close(self):
        if self.proc.returncode is None:  # timed out or failed: stop the whole script
            with suppress(ProcessLookupError):
                os.killpg(self.proc.pid, signal.SIGKILL)


class LocalHost:
    """Runs a machine's scripts on this computer (see managed.open_host)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def start(self, script: str) -> _Process:
        BASE.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            'sh',
            '-s',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=ENV,
            # Its own session: Ctrl-C or a reload of Open WebUI leaves Open Terminal running.
            start_new_session=True,
        )
        proc.stdin.write(script.encode())  # stdin, not argv: the API key never shows up in `ps`
        await proc.stdin.drain()
        proc.stdin.close()
        return _Process(proc)

    async def sh(self, script: str, *, timeout: float = 60) -> str:
        proc = await self.start(script)
        try:
            async with asyncio.timeout(timeout):
                text = (await proc.proc.stdout.read()).decode(errors='replace')
                code = await proc.wait()
        finally:
            proc.close()
        if code:
            raise MachineError(text.strip()[-2000:] or f'Command failed with exit code {code}.')
        return text

    def valid_root(self, root: str, machine_id: str) -> bool:
        return root == root_for(machine_id)

    async def transport(self, root: str) -> None:
        return None  # Open WebUI connects to the socket directly
