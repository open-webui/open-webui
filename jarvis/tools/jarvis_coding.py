"""
title: JARVIS Coding
author: JoshTXWC
description: Coding mode - search a codebase, read with line numbers, apply exact edits (shown as a diff you approve), run Python, and git status / commit / push on a feature branch. Ported from JoshTXWC/JARVIS coding_tools + code_tools.
version: 1.0.0
license: MIT
"""

import asyncio
import base64
import difflib
import fnmatch
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

# --- shared guard (inline on purpose: Open WebUI tools are single files) -----
SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", "credentials",
    "credentials.json", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "authorized_keys", "known_hosts", ".netrc", ".npmrc", ".pypirc",
    ".git-credentials", ".webui_secret_key", "webui.db",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx", ".keystore", ".jks")
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next",
             ".svelte-kit", "target", ".idea"}
SEARCH_FILE_MAX = 2_000_000       # skip (don't read) files bigger than this when searching
EDIT_FILE_MAX = 50 * 1024 * 1024  # refuse to edit files bigger than this - never truncate
_SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|Bearer\s+[A-Za-z0-9._\-]{16,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|AIza[0-9A-Za-z\-_]{20,})"
)


def redact(text: str) -> str:
    return _SECRET_VALUE_RE.sub("***REDACTED***", text or "")


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


def iter_code_files(root: Path, glob: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if glob and glob != "*" and not fnmatch.fnmatch(fn, glob):
                continue
            fp = Path(dirpath) / fn
            # Review fix: every file is checked against the secret denylist,
            # not just the folder that was searched.
            if is_secret_path(fp):
                continue
            yield fp


def unified(old: str, new: str, name: str, limit: int = 80) -> str:
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{name}", f"b/{name}", n=2, lineterm=""))
    if len(diff) > limit:
        diff = diff[:limit] + [f"... ({len(diff) - limit} more diff lines)"]
    return "\n".join(diff)


def read_whole_text(p: Path) -> str:
    """Read the entire file. Refuses (instead of truncating) when it is too big."""
    size = p.stat().st_size
    if size > EDIT_FILE_MAX:
        raise ValueError(f"{p.name} is {size} bytes; files over {EDIT_FILE_MAX} bytes are not edited")
    with open(p, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    return text


async def git(args: list, cwd: str, timeout: int = 120, extra_cfg: Optional[list] = None):
    argv = ["git"]
    for c in extra_cfg or []:
        argv += ["-c", c]
    argv += args
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError:
        return 127, "git is not installed or not on PATH (https://git-scm.com/download/win)"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, f"git {' '.join(args[:2])} timed out after {timeout}s"
    return proc.returncode or 0, redact((out or b"").decode("utf-8", "replace"))


async def switch_branch(br: str, cwd: str):
    """Move to `br` without ever resetting an existing branch (no `checkout -B`)."""
    code, _ = await git(["rev-parse", "--verify", "--quiet", f"refs/heads/{br}"], cwd)
    if code == 0:
        return await git(["switch", br], cwd)
    code, _ = await git(["rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{br}"], cwd)
    if code == 0:
        return await git(["switch", "--track", f"origin/{br}"], cwd)
    return await git(["switch", "-c", br], cwd)


class Tools:
    class Valves(BaseModel):
        ALLOWED_ROOTS: str = Field(default="~", description="Semicolon-separated folders coding tools may read/edit.")
        GITHUB_TOKEN: str = Field(
            default="", description="GitHub token for pushes. Empty = use the GITHUB_TOKEN env var, then your normal git credentials."
        )
        BACKUP_DIR: str = Field(default="~/.jarvis/backups", description="Where edit_file keeps a copy before each edit.")

    def __init__(self):
        self.valves = self.Valves()

    def _token(self) -> str:
        return (self.valves.GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN", "")).strip()

    def _auth_cfg(self) -> list:
        tok = self._token()
        if not tok:
            return []
        basic = base64.b64encode(f"x-access-token:{tok}".encode()).decode()
        return [f"http.https://github.com/.extraheader=AUTHORIZATION: basic {basic}"]

    def code_search(self, query: str, path: str = ".", glob: str = "*", regex: bool = False, max_results: int = 60) -> str:
        """
        Search text inside a codebase (like grep). Secret files (.env, keys, credentials) are always skipped.
        :param query: Text or regex to find.
        :param path: Project folder to search.
        :param glob: File-name filter, e.g. "*.py".
        :param regex: Treat query as a regular expression.
        :param max_results: Maximum matching lines.
        """
        try:
            root = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            rx = re.compile(query if regex else re.escape(query), re.IGNORECASE)
        except Exception as e:
            return f"Error: {e}"
        hits = []
        files = [root] if root.is_file() else iter_code_files(root, glob)
        for fp in files:
            try:
                if fp.stat().st_size > SEARCH_FILE_MAX:
                    continue
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if rx.search(line):
                            rel = fp.relative_to(root) if root.is_dir() else fp.name
                            hits.append(f"{rel}:{i}: {line.rstrip()[:240]}")
                            if len(hits) >= max_results:
                                return redact("\n".join(hits)) + "\n... (more matches truncated)"
            except (OSError, UnicodeDecodeError):
                continue
        return redact("\n".join(hits)) or "No matches."

    def read_code(self, path: str, start_line: int = 1, end_line: int = 400) -> str:
        """
        Read a source file with line numbers.
        :param path: File path.
        :param start_line: First line (1-based).
        :param end_line: Last line.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            out = []
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if i < start_line:
                        continue
                    if i > end_line:
                        out.append(f"... (more lines; call again with start_line={i})")
                        break
                    out.append(f"{i:5}| {line.rstrip()}")
            return "\n".join(out) or "(empty file)"
        except Exception as e:
            return f"Error: {e}"

    async def edit_file(
        self,
        path: str,
        new: str,
        old: str = "",
        replace_all: bool = False,
        create: bool = False,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Replace the exact text `old` with `new` in a file. Shows the diff and waits for the user to approve. Use create=true with empty old to make a new file.
        :param path: File path.
        :param new: Replacement text (or full content for a new file).
        :param old: Exact existing text to replace (copy it from read_code without line numbers).
        :param replace_all: Replace every match instead of requiring one.
        :param create: Create the file if it does not exist.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
            if not p.exists():
                if not create:
                    return f"File does not exist: {p} (set create=true to make it)"
                if not await confirm(__event_call__, "JARVIS: create file?", f"{p}\n\n{new[:1500]}"):
                    return "Cancelled: the user did not approve."
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
                return f"Created {p} ({len(new)} chars)."
            if not old:
                return "`old` is required to edit an existing file."
            text = read_whole_text(p)
            count = text.count(old)
            if count == 0:
                return f"`old` text not found in {p}. Read it with read_code and copy the exact text."
            if count > 1 and not replace_all:
                return f"`old` matches {count} places in {p}; include more surrounding lines or set replace_all=true."
            updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
            diff = unified(text, updated, p.name)
            if not await confirm(__event_call__, f"JARVIS: apply edit to {p.name}?", diff[:4000]):
                return "Cancelled: the user did not approve the edit."
            bdir = Path(os.path.expanduser(self.valves.BACKUP_DIR))
            bdir.mkdir(parents=True, exist_ok=True)
            backup = bdir / f"{p.name}.{time.strftime('%Y%m%d-%H%M%S')}.bak"
            shutil.copy2(p, backup)
            tmp = p.with_name(p.name + ".jarvis-tmp")
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(updated)
            os.replace(tmp, p)
            return f"Edited {p} (backup: {backup})\n{diff}"
        except Exception as e:
            return f"Error: {e}"

    async def run_python(
        self, code: str, cwd: str = "", timeout: int = 60,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Run a Python snippet on this PC after the user approves it, and return its output.
        :param code: Python source.
        :param cwd: Existing working folder (empty = user folder).
        :param timeout: Seconds before it is killed.
        """
        wd = Path(os.path.expanduser(cwd or "~")).resolve()
        if not wd.is_dir():
            return f"Error: working directory does not exist: {wd}. Nothing was run."
        if not await confirm(__event_call__, "JARVIS wants to run Python", f"{code[:3000]}\n\nin {wd}"):
            return "Cancelled: the user did not approve."
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            script = f.name
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script, cwd=str(wd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return f"Timed out after {timeout}s."
            return f"exit code {proc.returncode}\n{redact(out.decode('utf-8', 'replace'))[:20000]}"
        finally:
            os.unlink(script)

    async def git_status(self, path: str, diff: bool = False) -> str:
        """
        Show git branch, status, last commits and diff summary for a repository.
        :param path: Repository folder.
        :param diff: Include the full diff.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
        except Exception as e:
            return f"Error: {e}"
        parts = []
        for args in (["status", "-sb"], ["log", "--oneline", "-5"], ["diff", "--stat"]):
            code, out = await git(args, str(p))
            if code == 127:
                return out
            parts.append(f"$ git {' '.join(args)}\n{out.strip()}")
        if diff:
            _, out = await git(["diff"], str(p))
            parts.append("$ git diff\n" + out[:12000])
        return "\n\n".join(parts)

    async def git_commit_push(
        self,
        path: str,
        message: str,
        branch: str,
        push: bool = True,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Commit all changes on a feature branch and (optionally) push it. Never commits to main/master and never force-pushes. The user approves first.
        :param path: Repository folder.
        :param message: Commit message.
        :param branch: Feature branch, e.g. jarvis/fix-login. Created if missing; an existing branch is switched to, never reset.
        :param push: Push the branch to origin.
        """
        try:
            p = resolve_in_roots(path, self.valves.ALLOWED_ROOTS)
        except Exception as e:
            return f"Error: {e}"
        br = (branch or "").strip()
        if not re.match(r"^[A-Za-z0-9._/\-]{1,100}$", br) or br.startswith("-"):
            return "Invalid branch name."
        if br in {"main", "master"}:
            return "Refusing to commit to main/master. Use a feature branch and open a pull request."
        code, st = await git(["status", "--short"], str(p))
        if code:
            return st
        if not await confirm(
            __event_call__, "JARVIS: commit" + (" and push" if push else "") + "?",
            f"Repo: {p}\nBranch: {br}\nMessage: {message}\n\n{st[:2500]}",
        ):
            return "Cancelled: the user did not approve."
        log = []
        code, cur = await git(["rev-parse", "--abbrev-ref", "HEAD"], str(p))
        if code:
            return cur
        if cur.strip() != br:
            code, out = await switch_branch(br, str(p))
            log.append(out.strip())
            if code:
                log.append(f"Could not switch to {br}; nothing was committed.")
                return "\n".join(x for x in log if x)
        await git(["add", "-A"], str(p))
        code, out = await git(["commit", "-m", message], str(p))
        log.append(out.strip())
        if code and "nothing to commit" not in out:
            return "\n".join(log)
        if push:
            code, out = await git(["push", "-u", "origin", br], str(p), extra_cfg=self._auth_cfg(), timeout=300)
            log.append(out.strip())
            if code:
                log.append("Push failed - check your git credentials or the GITHUB_TOKEN valve.")
        return "\n".join(x for x in log if x)
