"""
title: JARVIS GitHub
author: JoshTXWC
description: GitHub access with your personal access token - list repos, read files, issues and PRs, clone into ~/JARVIS-Projects, and open pull requests (asks first). Ported from JoshTXWC/JARVIS github_tools.
version: 1.0.0
license: MIT
"""

import asyncio
import base64
import os
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

import aiohttp
from pydantic import BaseModel, Field

_REPO_RE = re.compile(r"^(?:https?://github\.com/)?([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git)?/?$")
_TOKEN_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")


def parse_repo(repo: str):
    m = _REPO_RE.match((repo or "").strip())
    if not m:
        raise ValueError("repo must look like owner/name or https://github.com/owner/name")
    return m.group(1), m.group(2)


async def confirm(event_call, title: str, message: str) -> bool:
    if event_call is None:
        return False
    try:
        return bool(await event_call({"type": "confirmation", "data": {"title": title, "message": message}}))
    except Exception:
        return False


class Tools:
    class Valves(BaseModel):
        GITHUB_TOKEN: str = Field(default="", description="Personal access token. Empty = use the GITHUB_TOKEN env var.")
        API_URL: str = Field(default="https://api.github.com")
        WORKSPACE_DIR: str = Field(default="~/JARVIS-Projects", description="Where github_clone puts repositories.")

    def __init__(self):
        self.valves = self.Valves()

    def _token(self) -> str:
        return (self.valves.GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN", "")).strip()

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "JARVIS-OpenWebUI"}
        if self._token():
            h["Authorization"] = f"Bearer {self._token()}"
        return h

    async def _req(self, method: str, path: str, params=None, json=None):
        url = self.valves.API_URL.rstrip("/") + path
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.request(method, url, headers=self._headers(), params=params, json=json) as r:
                body = await r.json(content_type=None)
                if r.status == 401:
                    raise RuntimeError("GitHub rejected the token (401). Check the GITHUB_TOKEN valve.")
                if r.status == 404:
                    raise RuntimeError("Not found (404): check the name, or the token cannot see it.")
                if r.status >= 400:
                    raise RuntimeError(f"GitHub API {r.status}: {str(body)[:300]}")
                return body

    async def github_status(self) -> str:
        """
        Check whether a GitHub token is set and which account it belongs to.
        """
        if not self._token():
            return "No GitHub token set. Add one in Workspace > Tools > JARVIS GitHub > Valves, or set GITHUB_TOKEN in jarvis.env."
        try:
            me = await self._req("GET", "/user")
            return f"Connected to GitHub as {me.get('login')}."
        except Exception as e:
            return f"Error: {e}"

    async def github_list_repos(self, owner: str = "", limit: int = 30) -> str:
        """
        List repositories (yours by default, or a user/org's).
        :param owner: User or org; empty = the token's own account.
        :param limit: Max repos.
        """
        try:
            path = f"/users/{owner}/repos" if owner else "/user/repos"
            data = await self._req("GET", path, params={"per_page": min(limit, 100), "sort": "updated"})
            return "\n".join(
                f"{r['full_name']}{' (private)' if r.get('private') else ''} - {r.get('description') or ''}" for r in data
            ) or "No repositories."
        except Exception as e:
            return f"Error: {e}"

    async def github_read_file(self, repo: str, path: str, ref: str = "") -> str:
        """
        Read a file from a GitHub repository.
        :param repo: owner/name.
        :param path: File path in the repo.
        :param ref: Branch, tag or commit (empty = default branch).
        """
        try:
            o, n = parse_repo(repo)
            data = await self._req("GET", f"/repos/{o}/{n}/contents/{path.lstrip('/')}", params={"ref": ref} if ref else None)
            if isinstance(data, list):
                return "\n".join(f"[{x['type']}] {x['path']}" for x in data)
            text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
            return text[:200000]
        except Exception as e:
            return f"Error: {e}"

    async def github_list_issues(self, repo: str, state: str = "open", limit: int = 20) -> str:
        """
        List issues in a repository (pull requests excluded).
        :param repo: owner/name.
        :param state: open, closed or all.
        :param limit: Max items.
        """
        try:
            o, n = parse_repo(repo)
            data = await self._req("GET", f"/repos/{o}/{n}/issues", params={"state": state, "per_page": min(limit, 100)})
            rows = [f"#{i['number']} {i['title']} ({i['state']})" for i in data if "pull_request" not in i]
            return "\n".join(rows) or "No issues."
        except Exception as e:
            return f"Error: {e}"

    async def github_list_pulls(self, repo: str, state: str = "open", limit: int = 20) -> str:
        """
        List pull requests in a repository.
        :param repo: owner/name.
        :param state: open, closed or all.
        :param limit: Max items.
        """
        try:
            o, n = parse_repo(repo)
            data = await self._req("GET", f"/repos/{o}/{n}/pulls", params={"state": state, "per_page": min(limit, 100)})
            return "\n".join(f"#{p['number']} {p['title']} ({p['head']['ref']} -> {p['base']['ref']})" for p in data) or "No pull requests."
        except Exception as e:
            return f"Error: {e}"

    async def github_clone(self, repo: str, branch: str = "", __event_call__: Optional[Callable[[dict], Awaitable]] = None) -> str:
        """
        Clone a GitHub repo into ~/JARVIS-Projects so the coding tools can work on it (pulls if already cloned).
        :param repo: owner/name or URL.
        :param branch: Optional branch.
        """
        try:
            o, n = parse_repo(repo)
        except Exception as e:
            return f"Error: {e}"
        ws = Path(os.path.expanduser(self.valves.WORKSPACE_DIR)).resolve()
        dest = ws / n
        ws.mkdir(parents=True, exist_ok=True)
        extra = []
        if self._token():
            basic = base64.b64encode(f"x-access-token:{self._token()}".encode()).decode()
            extra = ["-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {basic}"]
        if (dest / ".git").exists():
            args = ["git", *extra, "pull", "--ff-only"]
            cwd = dest
        else:
            args = ["git", *extra, "clone", "--depth", "50"] + (["--branch", branch] if branch else []) + [
                f"https://github.com/{o}/{n}.git", str(dest)]
            cwd = ws
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        out, _ = await proc.communicate()
        text = _TOKEN_RE.sub("***", out.decode("utf-8", "replace"))
        if proc.returncode:
            return f"git failed:\n{text}"
        return f"{o}/{n} is at {dest}\n{text}"

    async def github_create_pull_request(
        self, repo: str, head: str, title: str, base: str = "", body: str = "", draft: bool = False,
        __event_call__: Optional[Callable[[dict], Awaitable]] = None,
    ) -> str:
        """
        Open a pull request from a pushed branch. Visible to others, so the user approves first.
        :param repo: owner/name.
        :param head: Branch with the changes.
        :param title: PR title.
        :param base: Target branch (empty = default branch).
        :param body: PR description.
        :param draft: Open as a draft.
        """
        if not self._token():
            return "Set a GitHub token first (JARVIS GitHub valves or GITHUB_TOKEN)."
        try:
            o, n = parse_repo(repo)
            if not base:
                base = (await self._req("GET", f"/repos/{o}/{n}")).get("default_branch") or "main"
            if not await confirm(__event_call__, "JARVIS: open a pull request?", f"{o}/{n}: {head} -> {base}\n\n{title}\n\n{body[:1500]}"):
                return "Cancelled: the user did not approve."
            pr = await self._req("POST", f"/repos/{o}/{n}/pulls", json={"title": title, "head": head, "base": base, "body": body, "draft": draft})
            return f"Opened PR #{pr['number']}: {pr['html_url']}"
        except Exception as e:
            return f"Error: {e}"
