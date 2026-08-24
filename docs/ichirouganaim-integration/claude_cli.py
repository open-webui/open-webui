"""
title: Claude CLI
author: ichirouganaim-integration
description: Chats through a local Claude.ai subscription via the `claude` CLI, wired to the ichirouganaim MCP server.
version: 0.2.0
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

CLAUDE_RUNNER_USER = 'claude-runner'

# The claude CLI namespaces every MCP tool as mcp__<this key>__<tool> (e.g.
# mcp__ichirouganaim_mcp__get_record_graph_url) -- confirmed live, see
# decisions.md. Was 'mcp' (giving the redundant-looking mcp__mcp__<tool>)
# until renamed here; graph-url.ts's isGraphUrlTool() matches on a
# '__get_record_graph_url' suffix rather than hardcoding the full name, so
# it doesn't need updating when this changes.
MCP_SERVER_KEY = 'ichirouganaim_mcp'

# sessions.json (chat_id -> claude session_id) has no other eviction path --
# _forget_session_id only fires on a hard CLI failure, so a long-lived
# deployment's successful chats would otherwise accumulate here forever.
# Same bound and eviction strategy as the reference repo's own
# sessionIdByChatId (lib/claude-cli-provider.ts's MAX_SESSIONS), ported
# here since this file had no bound of its own before.
MAX_SESSIONS = 500


def _chown_recursive(path: Path, uid: int, gid: int) -> None:
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs:
            os.chown(os.path.join(root, name), uid, gid)
        for name in files:
            os.chown(os.path.join(root, name), uid, gid)


def _output_id(prefix: str) -> str:
    # Mirrors open_webui.utils.middleware.output_id's format so these items
    # look the same as native tool-calling's, even though that helper isn't
    # itself an importable public API.
    return f'{prefix}_{uuid.uuid4().hex[:24]}'


def _tool_result_text(content) -> str:
    # A real captured tool_result.content is already a JSON-encoded string
    # (see decisions.md's 2026-08-22 live-capture entry) -- passed through
    # as-is so ToolCallDisplay.svelte's own JSON.parse re-parses it for
    # pretty display. Only non-string shapes (not seen live yet, but the
    # MCP spec allows structured content) get serialized here.
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content)
    except (TypeError, ValueError):
        return str(content)


class Pipe:
    class Valves(BaseModel):
        MODEL: str = Field(
            default='', description='Optional --model override passed to the claude CLI (e.g. "opus"). Empty uses the CLI default.'
        )
        MCP_SERVER_URL: str = Field(
            default='',
            description=(
                'Base URL of the ichirouganaim MCP server, used to build --mcp-config. '
                'When empty, the CLI runs with its own default (unrestricted, permission-gated) '
                'tools instead of --strict-mcp-config + --tools "" + --permission-mode bypassPermissions '
                '-- that locked-down combo is only safe once a specific MCP server is the sole tool source.'
            ),
        )
        CLAUDE_CLI_PATH: str = Field(
            default='claude', description='Path to the claude CLI executable (installed on PATH inside the container by Dockerfile.claude-cli).'
        )

    def __init__(self):
        self.valves = self.Valves()

    def _sessions_file(self) -> Path:
        try:
            from open_webui.config import CACHE_DIR

            path = CACHE_DIR / 'functions' / 'claude_cli'
        except Exception:
            path = Path('/tmp/claude_cli')
        path.mkdir(parents=True, exist_ok=True)
        return path / 'sessions.json'

    def _load_sessions(self) -> dict:
        f = self._sessions_file()
        if not f.exists():
            return {}
        # Raw os-level fd, not Python's buffered open(mode='a+') -- see
        # _update_sessions' own comment for why: mixing O_APPEND with a
        # truncate-then-rewrite pattern is a real, confirmed-live bug, not
        # just a style choice.
        try:
            fd = os.open(f, os.O_RDONLY)
        except OSError:
            return {}
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            try:
                size = os.fstat(fd).st_size
                raw = os.pread(fd, size, 0) if size else b''
                return json.loads(raw.decode('utf-8')) if raw else {}
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError):
            return {}
        finally:
            os.close(fd)

    def _update_sessions(self, mutate) -> None:
        """Read-modify-write sessions.json under an exclusive file lock.

        With today's default (UVICORN_WORKERS=1, a single process/event
        loop), Python's own cooperative scheduling already serializes this
        -- there's no `await` between the read and the write, so no other
        coroutine can interleave. That protection disappears the moment
        anyone scales past one worker (separate OS processes, no shared
        GIL) -- confirmed live this is a real gap, not just theoretical,
        see decisions.md's concurrency-testing entry.

        Uses raw `os.open`/`os.pread`/`os.pwrite` (positioned I/O, no file
        offset involved) rather than Python's buffered `open(..., 'a+')` --
        **live-verified this matters, not a style preference**: an earlier
        version used `'a+'` + `seek(0)` + `truncate()` + `write()`, which
        looked correct and passed small/lightly-loaded tests, but under
        real concurrent load (50 processes racing, tested inside the real
        container) lost the majority of writes, reproducibly. O_APPEND
        (implied by `'a'`/`'a+'`) makes the kernel reposition every write
        to the file's *actual current* end-of-file at write time, which
        interacts badly with a prior `truncate()` under concurrent
        modification -- exactly the kind of subtle bug this project's own
        "verify live, don't assume" discipline exists to catch. Switching
        to flag-based `os.open` (no `O_APPEND`) plus `pread`/`pwrite`
        (explicit byte offsets, no reliance on any tracked file position)
        removed the failure entirely across repeated live stress tests --
        see decisions.md.

        `mutate` receives the current dict and returns the replacement.
        """
        f = self._sessions_file()
        fd = os.open(f, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                size = os.fstat(fd).st_size
                raw = os.pread(fd, size, 0) if size else b''
                try:
                    sessions = json.loads(raw.decode('utf-8')) if raw else {}
                except json.JSONDecodeError:
                    sessions = {}
                sessions = mutate(sessions)
                data = json.dumps(sessions).encode('utf-8')
                os.ftruncate(fd, 0)
                os.pwrite(fd, data, 0)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _remember_session_id(self, chat_id: str, session_id: str) -> None:
        def mutate(sessions: dict) -> dict:
            # Pop-then-set (not a plain overwrite) moves an already-present
            # chat_id to the end -- dict insertion order doesn't otherwise
            # change on reassigning an existing key, which would make the
            # eviction below evict by first-ever-use instead of by
            # least-recently-used.
            sessions.pop(chat_id, None)
            sessions[chat_id] = session_id
            while len(sessions) > MAX_SESSIONS:
                sessions.pop(next(iter(sessions)), None)
            return sessions

        self._update_sessions(mutate)

    def _forget_session_id(self, chat_id: str) -> None:
        def mutate(sessions: dict) -> dict:
            sessions.pop(chat_id, None)
            return sessions

        self._update_sessions(mutate)

    def _prepare_privilege_drop(self) -> tuple[int, int, str | None] | None:
        """Best-effort: if running as root and CLAUDE_RUNNER_USER exists,
        return (uid, gid, cwd) so the claude subprocess can run under that
        user instead of root -- the CLI refuses --permission-mode
        bypassPermissions as root (Dockerfile.claude-cli's whole reason for
        creating that user; see decisions.md). Returns None outside that
        specific container setup (e.g. a plain local run), where the
        subprocess just inherits the current user as before.
        """
        if os.geteuid() != 0:
            return None
        try:
            import pwd

            pw = pwd.getpwnam(CLAUDE_RUNNER_USER)
        except (ImportError, KeyError):
            return None

        cwd = None
        config_dir = os.environ.get('CLAUDE_CONFIG_DIR')
        if config_dir:
            config_path = Path(config_dir)
            config_path.mkdir(parents=True, exist_ok=True)

            # bubblewrap can't mount a fresh /proc inside this already-
            # unprivileged container; this tells the CLI's own sandbox to
            # bind-mount the container's existing /proc instead. Confirmed
            # live (via strace) that this exact path -- CLAUDE_CONFIG_DIR's
            # own settings.json, not $HOME/.claude/settings.json -- is what
            # the CLI actually reads for a non-root run. Merged in (not
            # overwritten) so any other settings.json content survives.
            settings_path = config_path / 'settings.json'
            try:
                settings = json.loads(settings_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                settings = {}
            settings.setdefault('sandbox', {})['enableWeakerNestedSandbox'] = True
            settings_path.write_text(json.dumps(settings), encoding='utf-8')

            _chown_recursive(config_path, pw.pw_uid, pw.pw_gid)

            cwd_path = config_path.parent / 'claude-cli-cwd'
            cwd_path.mkdir(parents=True, exist_ok=True)
            _chown_recursive(cwd_path, pw.pw_uid, pw.pw_gid)
            cwd = str(cwd_path)

        return pw.pw_uid, pw.pw_gid, cwd

    def _ensure_message_item(self, output: list[dict]) -> dict:
        """Return the trailing 'message' output item, creating one if the
        last item isn't already one -- mirrors middleware.py's own
        text-delta handling (utils/middleware.py:4732-4746) so a tool call
        in the middle of a reply starts a fresh message item after it,
        exactly like native tool-calling does.
        """
        if not output or output[-1].get('type') != 'message':
            output.append(
                {
                    'type': 'message',
                    'id': _output_id('msg'),
                    'status': 'in_progress',
                    'role': 'assistant',
                    'content': [{'type': 'output_text', 'text': ''}],
                }
            )
        return output[-1]

    def _append_output_text(self, output: list[dict], text: str) -> None:
        item = self._ensure_message_item(output)
        parts = item.setdefault('content', [])
        if parts and parts[-1].get('type') == 'output_text':
            parts[-1]['text'] += text
        else:
            parts.append({'type': 'output_text', 'text': text})

    def _append_tool_call(self, output: list[dict], block: dict) -> None:
        """`assistant`-type message -> `function_call` item. Only call_id,
        name and the now-complete input matter here; text/thinking blocks
        in the same message are the caller's job to skip (see pipe()) --
        mirrors ClaudeCliTranslator.handleAssistant in the reference repo's
        claude-cli-provider.ts, which reads tool_use the same way, from the
        same message type, for the same reason (deltas already streamed
        the text/thinking, and a tool_use block's input is only guaranteed
        complete once this checkpoint message arrives -- see decisions.md).
        """
        call_id = block.get('id', '')
        if any(item.get('type') == 'function_call' and item.get('call_id') == call_id for item in output):
            return
        output.append(
            {
                'type': 'function_call',
                'id': call_id or _output_id('fc'),
                'call_id': call_id,
                'name': block.get('name', ''),
                'arguments': json.dumps(block.get('input') or {}),
                'status': 'in_progress',
            }
        )

    def _append_tool_result(self, output: list[dict], block: dict) -> None:
        """`user`-type message's tool_result -> `function_call_output` item,
        and marks the matching function_call 'completed'/'failed'. Mirrors
        ClaudeCliTranslator.handleUser plus middleware.py's own
        function_call_output shape (utils/middleware.py:5117-5127) --
        `output` uses `input_text` there (not `output_text`), matched here
        for the same reason: structuredOutput.ts's getToolResultText only
        excludes `input_image`, so `input_text` renders identically.
        """
        call_id = block.get('tool_use_id', '')
        is_error = bool(block.get('is_error'))
        for item in output:
            if item.get('type') == 'function_call' and item.get('call_id') == call_id:
                item['status'] = 'failed' if is_error else 'completed'
                break
        output.append(
            {
                'type': 'function_call_output',
                'id': _output_id('fco'),
                'call_id': call_id,
                'output': [{'type': 'input_text', 'text': _tool_result_text(block.get('content'))}],
                'status': 'completed',
            }
        )

    async def _emit_output(
        self,
        output: list[dict],
        __event_emitter__,
        __chat_id__: str,
        __message_id__: str,
        *,
        persist: bool,
    ) -> None:
        if __event_emitter__:
            await __event_emitter__({'type': 'chat:completion', 'data': {'output': output}})

        if persist and __chat_id__ and __message_id__:
            try:
                from open_webui.models.chats import Chats
            except Exception:
                return
            try:
                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    __chat_id__, __message_id__, {'output': output}
                )
            except Exception:
                # Best-effort: the live websocket emit above already
                # updated the UI: a persistence failure here just means a
                # reload would show stale/incomplete output, not that the
                # in-flight response should be torn down over it.
                pass

    def _latest_user_text(self, body: dict) -> str:
        for message in reversed(body.get('messages', [])):
            if message.get('role') == 'user':
                content = message.get('content')
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return '\n'.join(part.get('text', '') for part in content if part.get('type') == 'text')
        return ''

    def _build_args(self, message: str, resume_session_id: str | None) -> list[str]:
        args = ['-p', message, '--output-format', 'stream-json', '--include-partial-messages', '--verbose']

        if self.valves.MCP_SERVER_URL:
            mcp_config = json.dumps({'mcpServers': {MCP_SERVER_KEY: {'type': 'http', 'url': self.valves.MCP_SERVER_URL}}})
            # This combo is only safe together: --strict-mcp-config + --tools ""
            # remove every other tool before --permission-mode bypassPermissions
            # waives approval for what's left (the one configured MCP server).
            args += ['--mcp-config', mcp_config, '--strict-mcp-config', '--tools', '', '--permission-mode', 'bypassPermissions']

        if self.valves.MODEL:
            args += ['--model', self.valves.MODEL]
        if resume_session_id:
            args += ['--resume', resume_session_id]

        return args

    async def pipe(
        self,
        body: dict,
        __chat_id__: str = '',
        __message_id__: str = '',
        __event_emitter__=None,
        __user__=None,
    ):
        message = self._latest_user_text(body)
        if not message:
            yield '[claude-cli] No user message to send.'
            return

        sessions = self._load_sessions()
        resume_session_id = sessions.get(__chat_id__) if __chat_id__ else None
        args = self._build_args(message, resume_session_id)

        spawn_kwargs: dict = {
            'stdout': asyncio.subprocess.PIPE,
            'stderr': asyncio.subprocess.PIPE,
            # asyncio.StreamReader's default line-buffer limit is 64KB;
            # a single stream-json line carrying a large MCP tool result
            # (e.g. a full get_workflow response) blows past that and
            # raises LimitOverrunError ("Separator is found, but chunk is
            # longer than limit") -- confirmed live via a real deed-entry
            # prompt that pulls the full workflow definition. 32MB comfortably
            # covers realistic tool results without being unbounded.
            'limit': 32 * 1024 * 1024,
        }
        argv = [self.valves.CLAUDE_CLI_PATH, *args]

        drop = self._prepare_privilege_drop()
        if drop:
            uid, gid, cwd = drop
            # asyncio's own user=/group= subprocess kwargs (the normal way
            # to do this) raise "unexpected kwargs: user, group" under
            # uvloop -- this container's event loop implementation --
            # confirmed live. setpriv (util-linux, already present in the
            # base image) does the same privilege drop as a wrapping
            # command instead, taking argv directly so the user's message
            # text never passes through a shell to be escaped.
            argv = ['setpriv', f'--reuid={uid}', f'--regid={gid}', '--clear-groups', *argv]
            if cwd:
                spawn_kwargs['cwd'] = cwd

        try:
            proc = await asyncio.create_subprocess_exec(*argv, **spawn_kwargs)
        except OSError as e:
            yield f'[claude-cli] Failed to run the claude CLI ({self.valves.CLAUDE_CLI_PATH}): {e}'
            return

        open_text_blocks: set[int] = set()
        saw_result = False
        stderr_chunks: list[bytes] = []
        output: list[dict] = []

        async def drain_stderr():
            async for chunk in proc.stderr:
                stderr_chunks.append(chunk)

        stderr_task = asyncio.create_task(drain_stderr())

        try:
            async for raw_line in proc.stdout:
                line = raw_line.decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                session_id = obj.get('session_id')
                if isinstance(session_id, str) and __chat_id__:
                    self._remember_session_id(__chat_id__, session_id)

                obj_type = obj.get('type')
                if obj_type == 'stream_event':
                    event = obj.get('event') or {}
                    event_type = event.get('type')
                    index = event.get('index')

                    if event_type == 'content_block_start':
                        block = event.get('content_block') or {}
                        if block.get('type') == 'text':
                            open_text_blocks.add(index)
                    elif event_type == 'content_block_delta' and index in open_text_blocks:
                        delta = event.get('delta') or {}
                        if delta.get('type') == 'text_delta':
                            text = delta.get('text', '')
                            yield text
                            # Also mirror into `output` as a `message` item --
                            # ContentRenderer.svelte renders *only* from
                            # `output` once it's non-empty (confirmed live,
                            # see decisions.md), so once a tool call adds a
                            # function_call item this turn, the plain-text
                            # SSE content above would otherwise stop being
                            # displayed at all.
                            self._append_output_text(output, text)
                            await self._emit_output(
                                output, __event_emitter__, __chat_id__, __message_id__, persist=False
                            )
                    elif event_type == 'content_block_stop':
                        open_text_blocks.discard(index)
                        if output:
                            await self._emit_output(
                                output, __event_emitter__, __chat_id__, __message_id__, persist=True
                            )

                elif obj_type == 'assistant':
                    cli_message = obj.get('message') or {}
                    for block in cli_message.get('content') or []:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            self._append_tool_call(output, block)
                    if output:
                        await self._emit_output(
                            output, __event_emitter__, __chat_id__, __message_id__, persist=True
                        )

                elif obj_type == 'user':
                    cli_message = obj.get('message') or {}
                    for block in cli_message.get('content') or []:
                        if isinstance(block, dict) and block.get('type') == 'tool_result':
                            self._append_tool_result(output, block)
                    if output:
                        await self._emit_output(
                            output, __event_emitter__, __chat_id__, __message_id__, persist=True
                        )

                elif obj_type == 'result':
                    saw_result = True
                    if obj.get('is_error'):
                        result = obj.get('result')
                        detail = result if isinstance(result, str) else f"claude exited with an error (subtype: {obj.get('subtype', 'unknown')})."
                        yield f'\n\n[claude-cli error] {detail}'
        except asyncio.LimitOverrunError as e:
            proc.kill()
            yield f'\n\n[claude-cli error] A single response line exceeded the {spawn_kwargs["limit"]}-byte read buffer ({e}). Likely an unusually large tool result.'
            if output:
                await self._emit_output(output, __event_emitter__, __chat_id__, __message_id__, persist=True)
            await proc.wait()
            return

        if output:
            await self._emit_output(output, __event_emitter__, __chat_id__, __message_id__, persist=True)

        await proc.wait()
        await stderr_task

        if proc.returncode != 0 and not saw_result:
            if __chat_id__:
                self._forget_session_id(__chat_id__)
            stderr_text = b''.join(stderr_chunks).decode('utf-8', errors='replace')
            yield f'\n\n[claude-cli error] exited with code {proc.returncode}: {stderr_text[:500]}'
