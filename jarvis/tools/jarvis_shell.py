"""
title: JARVIS Shell
author: JoshTXWC
description: Run cmd / PowerShell / bash commands on this PC after you approve each one in the chat. Ported from JoshTXWC/JARVIS shell_tools.
version: 1.0.0
license: MIT
"""

import asyncio
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

_SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|Bearer\s+[A-Za-z0-9._\-]{16,}"
    r"|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|AIza[0-9A-Za-z\-_]{20,})"
)
_EXFIL_RE = re.compile(
    r"(?i)(\.env\b|id_rsa|id_ed25519|\.ssh[\\/]|credential|\.git-credentials|webui_secret_key"
    r"|\bcmdkey\b|vaultcmd|Get-StoredCredential|printenv|\bset\s*$|Get-ChildItem\s+env:|\bgci\s+env:|\bdir\s+env:)"
)


def redact(text: str) -> str:
    return _SECRET_VALUE_RE.sub("***REDACTED***", text or "")


def resolve_cwd(cwd: str, default: str) -> Path:
    """Return an existing working directory or raise. Never silently falls back
    to another folder: a mistyped cwd must not run the command somewhere else."""
    raw = (cwd or "").strip() or default
    p = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
    if not p.exists():
        raise FileNotFoundError(f"working directory does not exist: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"working directory is not a folder: {p}")
    return p


async def confirm(event_call, title: str, message: str) -> bool:
    if event_call is None:
        return False
    try:
        return bool(await event_call({"type": "confirmation", "data": {"title": title, "message": message}}))
    except Exception:
        return False


async def run(argv: list, cwd: Path, timeout: int) -> str:
    proc = await asyncio.create_subprocess_exec(
        *argv, cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=max(1, int(timeout)))
    except asyncio.TimeoutError:
        proc.kill()
        return f"Timed out after {timeout}s (process killed)."
    text = out.decode("utf-8", errors="replace")
    if len(text) > 20000:
        text = text[:10000] + "\n... [output truncated] ...\n" + text[-10000:]
    return f"exit code {proc.returncode} (cwd {cwd})\n{redact(text)}"


class Tools:
    class Valves(BaseModel):
        DEFAULT_CWD: str = Field(default="~", description="Folder used when no cwd is given.")
        TIMEOUT_MAX: int = Field(default=600, description="Upper limit for command timeouts in seconds.")

    def __init__(self):
        self.valves = self.Valves()

    async def _exec(self, shell_name: str, argv: list, command: str, cwd: str, timeout: int, event_call) -> str:
        if _EXFIL_RE.search(command or ""):
            return "DENIED: the command looks like it reads secrets or credentials."
        try:
            wd = resolve_cwd(cwd, self.valves.DEFAULT_CWD)
        except Exception as e:
            return f"Error: {e}. Nothing was run."
        if not await confirm(event_call, f"JARVIS wants to run ({shell_name})", f"{command}\n\nin {wd}"):
            return "Cancelled: the user did not approve this command."
        return await run(argv, wd, min(int(timeout), self.valves.TIMEOUT_MAX))

    async def run_shell(
        self,
        command: str,
        cwd: str = "",
        timeout: int = 60,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Run a shell command (cmd.exe on Windows, bash elsewhere). The user approves each command first.
        :param command: The command line to run.
        :param cwd: Existing working folder. Leave empty to use the default folder.
        :param timeout: Seconds before the command is killed.
        """
        argv = ["cmd.exe", "/d", "/s", "/c", command] if os.name == "nt" else ["/bin/bash", "-lc", command]
        return await self._exec("shell", argv, command, cwd, timeout, __event_call__)

    async def run_powershell(
        self,
        command: str,
        cwd: str = "",
        timeout: int = 60,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Run a PowerShell command. The user approves each command first.
        :param command: PowerShell command.
        :param cwd: Existing working folder. Leave empty to use the default folder.
        :param timeout: Seconds before the command is killed.
        """
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        argv = [exe, "-NoProfile", "-NonInteractive", "-Command", command]
        return await self._exec("PowerShell", argv, command, cwd, timeout, __event_call__)

    def which(self, program: str) -> str:
        """
        Find where a program is installed (like `where` / `which`).
        :param program: Program name, e.g. git, node, python.
        """
        found = shutil.which(program)
        return found or f"{program} not found on PATH"

    def system_info(self) -> str:
        """
        Basic info about this computer: OS, Python, CPU count, disk free space.
        """
        import platform

        total, used, free = shutil.disk_usage(Path.home().anchor or "/")
        return (
            f"OS: {platform.platform()}\nMachine: {platform.node()}\nPython: {sys.version.split()[0]}\n"
            f"CPUs: {os.cpu_count()}\nDisk free: {free // (1024**3)} GB of {total // (1024**3)} GB"
        )
