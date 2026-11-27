"""
title: JARVIS Files
author: JoshTXWC
description: Read, list, search and (with your approval) write files on this PC. Ported from JoshTXWC/JARVIS file_tools.
version: 1.0.0
license: MIT
"""

import fnmatch
import os
from pathlib import Path
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

# --- shared guard (kept inline: Open WebUI tools must be single files) -------
SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", "credentials",
    "credentials.json", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "authorized_keys", "known_hosts", ".netrc", ".npmrc", ".pypirc",
    ".git-credentials", ".webui_secret_key", "webui.db",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx", ".keystore", ".jks")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".svelte-kit", "dist", "build"}
MAX_READ_BYTES = 512 * 1024


def is_secret_path(p: Path) -> bool:
    name = p.name.lower()
    if name in SECRET_NAMES or name.startswith(".env."):
        return True
    if name.endswith(SECRET_SUFFIXES):
        return True
    parts = {x.lower() for x in p.parts}
    return ".ssh" in parts or ".gnupg" in parts


def resolve_in_roots(path: str, roots_csv: str) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(path or "."))).resolve()
    roots = [Path(os.path.expandvars(os.path.expanduser(r.strip()))).resolve()
             for r in (roots_csv or "~").split(";") if r.strip()]
    for r in roots:
        try:
            p.relative_to(r)
            break
        except ValueError:
            continue
    else:
        raise PermissionError(f"path outside allowed roots: {p} (allowed: {'; '.join(map(str, roots))})")
    if is_secret_path(p):
        raise PermissionError(f"access denied to sensitive file: {p.name}")
    return p


async def confirm(event_call, title: str, message: str) -> bool:
    if event_call is None:
        return False
    try:
        return bool(await event_call({"type": "confirmation", "data": {"title": title, "message": message}}))
    except Exception:
        return False
# -----------------------------------------------------------------------------


class Tools:
    class Valves(BaseModel):
        ALLOWED_ROOTS: str = Field(
            default="~",
            description="Semicolon-separated folders JARVIS may touch (default: your user folder).",
        )
        REQUIRE_APPROVAL_FOR_WRITES: bool = Field(
            default=True, description="Ask in the chat before writing, moving or deleting."
        )

    def __init__(self):
        self.valves = self.Valves()

    def list_dir(self, path: str = ".") -> str:
        """
        List files and folders in a directory on this PC.
        :param path: Folder path. "~" is the user folder.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            if not p.is_dir():
                return f"Not a directory: {p}"
            rows = []
            for c in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:500]:
                if c.is_dir():
                    rows.append(f"[dir]  {c.name}/")
                else:
                    try:
                        rows.append(f"[file] {c.name}  ({c.stat().st_size} bytes)")
                    except OSError:
                        rows.append(f"[file] {c.name}")
            return f"{p}\n" + "\n".join(rows) if rows else f"{p} is empty"
        except Exception as e:
            return f"Error: {e}"

    def read_file(self, path: str, max_bytes: int = MAX_READ_BYTES) -> str:
        """
        Read a text file on this PC.
        :param path: File path.
        :param max_bytes: Maximum bytes to return (default 512 KB).
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            if not p.is_file():
                return f"Not a file: {p}"
            limit = max(1, min(int(max_bytes), MAX_READ_BYTES))
            with open(p, "rb") as f:
                data = f.read(limit + 1)
            text = data[:limit].decode("utf-8", errors="replace")
            if len(data) > limit:
                text += f"\n... [truncated at {limit} bytes; file is {p.stat().st_size} bytes]"
            return text
        except Exception as e:
            return f"Error: {e}"

    def search_files(self, pattern: str, path: str = ".", max_results: int = 200) -> str:
        """
        Find files by glob pattern (e.g. "*.py", "*report*") under a folder.
        :param pattern: Glob pattern matched against file names.
        :param path: Folder to search.
        :param max_results: Maximum results.
        """
        try:
            root = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            hits = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for fn in filenames:
                    if fnmatch.fnmatch(fn.lower(), pattern.lower()):
                        fp = Path(dirpath) / fn
                        if not is_secret_path(fp):
                            hits.append(str(fp))
                            if len(hits) >= max_results:
                                return "\n".join(hits) + "\n... (more results truncated)"
            return "\n".join(hits) or "No matches."
        except Exception as e:
            return f"Error: {e}"

    async def write_file(
        self,
        path: str,
        content: str,
        append: bool = False,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Create or overwrite (or append to) a text file. Asks the user to approve first.
        :param path: File path.
        :param content: Text to write.
        :param append: Append instead of overwrite.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            verb = "Append to" if append else ("Overwrite" if p.exists() else "Create")
            if self.valves.REQUIRE_APPROVAL_FOR_WRITES and not await confirm(
                __event_call__, f"JARVIS: {verb} file?", f"{p}\n\n{len(content)} characters"
            ):
                return "Cancelled: the user did not approve the write."
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a" if append else "w", encoding="utf-8", newline="") as f:
                f.write(content)
            done = {"Append to": "Appended to", "Overwrite": "Overwrote", "Create": "Created"}[verb]
            return f"{done} {p} ({len(content)} chars)."
        except Exception as e:
            return f"Error: {e}"

    async def delete_path(
        self, path: str, __event_call__: Optional[Callable[[dict], Awaitable]] = None
    ) -> str:
        """
        Delete a file or an empty folder. Always asks the user to approve first.
        :param path: File or empty folder path.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            if not p.exists():
                return f"Does not exist: {p}"
            if not await confirm(__event_call__, "JARVIS: Delete?", str(p)):
                return "Cancelled: the user did not approve the delete."
            if p.is_dir():
                p.rmdir()
            else:
                p.unlink()
            return f"Deleted {p}."
        except Exception as e:
            return f"Error: {e}"
