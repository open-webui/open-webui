# Decisions log — claude-cli + graph-url integration

One entry per real decision or fix. See `scoping-claude-cli-and-graph-modal.md`
for the overall plan; this file only records things discovered or decided
while building it.

## 2026-08-21 — Sync script: create-then-fallback-to-update, not GET-then-branch

**Verified against live code**, not assumed: `GET /api/v1/functions/id/{id}`
(`backend/open_webui/routers/functions.py:269-279`) returns **401**, not 404,
when the id doesn't exist — `get_function_by_id` raises
`HTTPException(401, ERROR_MESSAGES.NOT_FOUND)` in the not-found branch, which
would be indistinguishable from a real auth failure if `sync_pipe.py` used it
to decide create-vs-update.

Instead `sync_pipe.py` always tries `POST /api/v1/functions/create` first,
and only falls back to `POST /api/v1/functions/id/{id}/update` if the create
response is `400` with `ERROR_MESSAGES.ID_TAKEN` ("already registered") in
the detail (`backend/open_webui/constants.py:55`). This can't confuse
not-found with unauthorized, since a real auth failure surfaces as an error
on the create call itself and the script exits non-zero.

## 2026-08-21 — Sync script auto-activates on first create

**Verified against live code**: `FunctionForm` (used by both `/create` and
`/id/{id}/update`) has no `is_active` field
(`backend/open_webui/models/functions.py:98-102`), and `insert_new_function`
builds the stored row from `FunctionModel`'s own default
(`is_active: bool = False`, same file:43-56) — so every function starts
disabled. `get_function_models()`
(`backend/open_webui/functions.py:75`) only lists
`Functions.get_functions_by_type('pipe', active_only=True)`, so a freshly
created Pipe silently would not appear in the model dropdown at all.

`sync_pipe.py` calls `POST /api/v1/functions/id/{id}/toggle` immediately
after a successful create (never after an update, since toggle *flips*
state rather than setting it, and an update shouldn't touch whatever
active/inactive state the admin has already set). If the toggle call itself
fails, the script still reports the create as successful but tells the user
to activate it manually in Admin > Functions.

## 2026-08-21 — Sync script uses only the stdlib (`urllib`), no `requests`

Kept the dev-loop script dependency-free since it runs outside the backend's
own venv/import path (it POSTs to the running instance's HTTP API, it
doesn't import backend code). Avoids "pip install requests" being a
precondition to the "edit the file, run the script" loop the scoping doc
asks for.

## 2026-08-21 — Function id fixed as `claude_cli`

`FunctionForm.id` must satisfy `str.isidentifier()`
(`backend/open_webui/routers/functions.py:206-210`) and gets lowercased.
`claude_cli` (matching the stub source file's stem,
`docs/ichirouganaim-integration/claude_cli.py`) satisfies this and is what
`sync_pipe.py` derives by default from the filename stem, so no `--id` flag
is needed for the normal dev loop.

## 2026-08-21 — Build order steps 1-2 verified live against a real instance

Started the fork's own docker compose stack (`docker-compose.yaml` +
`docker-compose.override.yaml`, an existing but stopped `open-webui`
container from a prior session — no fresh data lost). Confirmed live, not
assumed:

- `ENABLE_API_KEYS` defaults to `False` and wasn't set in the container's
  env, so API-key auth was off. Enabled it via `Config.upsert({'auth.
  enable_api_keys': True})` (`backend/open_webui/models/config.py:191-213`)
  and generated an admin API key via `Users.update_user_api_key_by_id` +
  `create_api_key()` (`backend/open_webui/models/users.py:707-716`,
  `backend/open_webui/utils/auth.py:304-306`), run in-process inside the
  container (`docker exec -w /app/backend open-webui python3 ...`, with
  `WEBUI_SECRET_KEY` sourced from `.webui_secret_key` the same way
  `start.sh` does it — running a bare script skips that startup step, and
  the app hard-fails without it).
- `sync_pipe.py docs/ichirouganaim-integration/claude_cli.py` against the
  running instance: `Created and activated function "claude_cli".`
- `GET /api/models` lists `claude_cli` with `pipe.type: "pipe"` — the
  model-dropdown registration confirmed above (functions.py:75,132-142)
  works end to end, not just by code reading.
- `POST /api/chat/completions` with `model: "claude_cli", stream: true`
  streamed the stub's canned text as proper
  `chat.completion.chunk`/`[DONE]` SSE, confirming the async-generator
  `pipe()` -> `execute_pipe`/`process_line` path
  (`backend/open_webui/functions.py:154-174,328`) works as documented, not
  just as read.

Build order steps 1 and 2 (sync script, stubbed Pipe with plain streaming)
are done. Step 3 (real `claude` subprocess + JSONL translation) needs a
live `claude` CLI invocation — paused there per the standing "ask before
spending subscription usage" agreement.

## 2026-08-21 — The `claude` CLI wasn't reachable anywhere; installed it standalone, not via the frontend

Discovered live (not assumed) while starting step 3: `claude` was on
neither this host's `PATH` nor inside the `open-webui` Docker container
(no node/npm in that container image either). It existed only as
`ichirouganaim_frontend`'s own project-local `node_modules/.bin/claude`
(`@anthropic-ai/claude-code` as a regular devDependency, not a global
install) — user flagged that coupling this integration to a sibling
project's `node_modules` was wrong.

A user-scope global npm install (`npm install -g`) failed on `EACCES`
(`/usr/local/lib/node_modules` isn't user-writable on this machine, no
`sudo` used). Installed it instead as its own self-contained package at
`docs/ichirouganaim-integration/claude-cli-bin/` (`npm init -y && npm
install @anthropic-ai/claude-code`; `node_modules/` is already covered by
the repo's root `.gitignore`, confirmed before relying on it). This mirrors
exactly what the frontend did (a project-local install), just owned by
*this* integration's own directory instead of reusing the sibling repo.

Confirmed the CLI's login/session lives in `~/.claude` and `~/.claude.json`
(the user's home directory), not inside whichever `node_modules` happens to
contain the binary — so this fresh install picked up the existing
Claude.ai login automatically, no re-auth needed.

## 2026-08-21 — Step 3 verified live, but *not* through the containerized instance — a real deployment gap

**Live-verified, not assumed**: ran `Pipe.pipe()` from
`docs/ichirouganaim-integration/claude_cli.py` directly (a small host-side
harness script, not committed — it just imports the class and drives the
async generator), pointed at the newly-installed local CLI binary:

- Plain single-turn call: streamed real text
  (`content_block_delta`/`text_delta` -> bare-string `yield`, exactly the
  reference's mapping) and wrote a real session id to
  `CACHE_DIR/functions/claude_cli/sessions.json`.
- Two-turn continuity: a second call with the same `__chat_id__` resumed
  the first call's session (`--resume <id>`, loaded from that same JSON
  file) and correctly recalled state ("42") from turn one — confirms the
  `sessionIdByChatId` mechanism (JSON-file version, per the scoping doc's
  recommendation over an in-memory dict) works end to end, not just that
  the file gets written.
- Had to add `from __future__ import annotations` to `claude_cli.py` —
  found because the host's system Python is 3.9 (`str | None` PEP 604
  syntax fails eager evaluation there), while the actual open-webui
  container runs Python 3.11 where it would've been silently fine. Fixed
  anyway since it's the existing convention across this fork's own backend
  files (e.g. `backend/open_webui/models/functions.py`,
  `backend/open_webui/config.py`) and costs nothing.

**Not yet verified**: chatting with `claude_cli` through the actual running
`open-webui` container. That container has no `claude` binary reachable
(confirmed above) and, more fundamentally, no access to the host's
Keychain-backed CLI auth even if a binary were copied in — a Linux
container can't read a macOS Keychain entry. The Pipe's `OSError` handling
(`claude_cli.py`'s `pipe()`, the `except OSError` around
`create_subprocess_exec`) means this fails cleanly with a visible chat
message rather than crashing, so it's safe to leave synced, but **it will
not actually work through the containerized instance until this is
resolved** — open question for the user: run the fork's backend natively
(`backend/dev.sh`, already a supported path in this repo, so the process
spawning the subprocess is a normal host process with real Keychain
access) instead of via Docker for this feature, or find another way to get
CLI auth into the container.

## 2026-08-21 — Switched to native backend; migrated data from Docker; caught a mid-copy DB hazard

User chose "run backend natively." Steps taken, each confirmed live:

- No Python 3.11 on the host (`pyproject.toml:130` requires `>= 3.11, <
  3.13`; host had 3.9.6 only). Used `uv python install 3.11` + `uv venv
  --python 3.11 .venv` + `uv pip install -r backend/requirements.txt`
  rather than touching system Python — self-contained, gitignored
  (`.venv` matches the repo's existing `node_modules`-style ignore
  pattern), fully reversible.
- Copied the Docker container's `/app/backend/data` (the actual
  `open-webui` named volume's contents: `webui.db`, uploads, vector_db,
  function cache including `claude_cli`'s `sessions.json`) into
  `backend/data/` so the admin account, the synced `claude_cli` function,
  and the API key created earlier all carry over instead of starting
  fresh. Also copied `/app/backend/.webui_secret_key` separately -- it's
  not part of the data volume (lives in the container's own layer,
  `start.sh:32-51`), and JWT signing / `OAUTH_*_ENCRYPTION_KEY` defaults
  (`backend/open_webui/env.py:716-819`) both key off it, so a *new*
  generated secret would silently break decrypting anything already
  encrypted with the old one. Both paths confirmed gitignored
  (`backend/.gitignore:10,12`) before relying on that.
- **First native start hung indefinitely** after only 2 log lines
  (`alembic.runtime.migration`), CPU dropping to idle with no further
  progress and no listening socket. Root cause: `docker cp`'d the SQLite
  `-wal`/`-shm` files *while the container was still running* (copied
  before `docker stop`, not after) -- those files are only safe to copy
  verbatim once nothing holds them open; mid-write copies can leave the
  WAL-index in a state a fresh process can't cleanly recover, which reads
  as a silent hang rather than a clean error. Fixed by re-copying from the
  now-fully-stopped container (`docker ps -a` confirmed `Exited`) and
  running `sqlite3 webui.db "PRAGMA wal_checkpoint(TRUNCATE);"` before the
  second start attempt, which folded the WAL into the main file and zeroed
  it out (`0|0|0` = clean checkpoint) -- worth remembering for any future
  "copy a running SQLite-backed container's volume" step, not just this
  one: stop first, or checkpoint first, never neither.
- Native backend now serves API-only (no built `build/` frontend directory
  present outside the Docker image, expected -- `open_webui.main`'s own
  warning: `Frontend build directory not found... Serving API only`).
  Fine for verifying the Pipe/chat-completions path; a browser UI check
  (needed for Part 2 and the "Consistency requirement" section) will need
  either building the frontend or running its own Vite dev server
  separately -- not done yet.
- Set the `claude_cli` function's `CLAUDE_CLI_PATH` valve (via `POST
  /api/v1/functions/id/claude_cli/valves/update`) to the absolute path of
  the standalone local install (`docs/ichirouganaim-integration/claude-cli-bin/node_modules/.bin/claude`)
  rather than leaving the bare `claude` default, since the native
  `uvicorn` process's `PATH` has no reason to include that project-local
  `node_modules/.bin`.
- **Full path live-verified**: `POST /api/chat/completions` against
  `http://localhost:8080` (the native process) with `model: "claude_cli"`
  streamed a real `claude` CLI response end to end -- actual subprocess,
  actual JSONL translation, actual SSE chunks out of the real HTTP API,
  not the harness script from the previous entry. This is the first time
  the *whole* stack (open-webui HTTP API -> Pipe -> real claude CLI ->
  translated stream -> SSE response) has been confirmed working together.

Docker container `open-webui` is stopped (not removed) -- can be restarted
if ever needed, but the native process at `:8080` is the one with a
working `claude_cli` model going forward. `:3000` (Docker) is idle.

## 2026-08-21 — Reverted the native detour: user corrected the scope back to Docker-only

User pushback: the project's scope is additions to this repo/fork's normal
Docker-based deployment, not standing up a second, diverging native
instance. Fair -- the previous entry's "run natively instead" was solving
the *symptom* (this host's `claude` CLI can't run inside the stock
container) by routing around Docker entirely, not the actual problem
(getting `claude` reachable *inside* the container people actually run).
Reverted:

- Killed the native `uvicorn`/`vite dev` processes.
- `docker start open-webui` -- its data volume was never touched by the
  native copy (only a host-side copy of it was), so this came back exactly
  as it was left, no data lost on either side.
- Deleted the stale copied `backend/data/*` (webui.db + uploads + vector_db
  + cache), `backend/.webui_secret_key`, `.venv`, and `node_modules` --
  all artifacts of the abandoned native path, all gitignored, all safe to
  remove.

## 2026-08-21 — Getting `claude` to actually run *inside* the Docker container: two real, live-verified obstacles

Set out to solve the actual problem this time: `claude` CLI reachable
*from inside* the `open-webui` container, not routed around it.

**Obstacle 1, live-verified**: bind-mounting the host's already-installed
CLI (`docs/ichirouganaim-integration/claude-cli-bin/node_modules`) into a
throwaway `node:20-bookworm-slim` container and running it directly failed
with `Exec format error`. Cause: `@anthropic-ai/claude-code`'s own
`package.json` lists per-OS/arch `optionalDependencies`
(`claude-code-darwin-arm64`, `-linux-x64`, `-linux-arm64`, ...) -- npm's
platform detection at install time picks the one matching the *installing*
machine, so the host's macOS install physically cannot run inside a Linux
container. Fix: the CLI has to be `npm install`ed *from inside* a Linux
environment (the container itself, at image build time) so npm resolves
the Linux-arm64 variant instead.

**Obstacle 2, live-verified**: even with the correct Linux binary, `claude
auth status` inside a throwaway container with the host's `~/.claude` and
`~/.claude.json` bind-mounted in (read-only) reported
`{"loggedIn": false, "authMethod": "none"}`. The actual OAuth session
token lives in macOS Keychain, not in either of those files -- confirmed
by the sandbox itself refusing a direct `security find-generic-password`
lookup for the credential (correctly; extracting a live OAuth secret out
of Keychain to move it elsewhere isn't something to do quietly). No
attempt made to work around that block. Conclusion: there is no way to
carry over the *host's* login into a Linux container; the container needs
its **own** independent login instead, established via `claude auth
login`'s normal browser-based OAuth flow run *inside* the container --
same mechanism a fresh headless/server install would use, not a copy of
anyone's existing session.

**`CLAUDE_CONFIG_DIR` confirmed live** as the way to relocate where that
login gets persisted: ran a throwaway container with
`-e CLAUDE_CONFIG_DIR=/data/claude-config -v claude_cli_home_test:/data/claude-config`
and confirmed the CLI wrote `.claude.json` + `backups/` there instead of
the default `~/.claude` -- not documented in `--help`, only confirmed by
trying it. This is what lets the container's login survive container
recreation without needing a brand-new named volume: pointed it at
`/app/backend/data/claude-cli-home`, a subdirectory of the *existing*
persistent data volume (`open-webui:/app/backend/data`, already declared
in `docker-compose.yaml`), rather than adding a new volume to declare and
manage.

**apt-get inside the build was broken, unrelated to any of the above**:
`apt-get install nodejs npm` failed GPG verification on every Debian
mirror (`At least one invalid signature was encountered`) -- this sandbox
environment's system clock reads 2026-08-22, and Debian's shipped archive
keyring has keys that read as expired against that date (this is an
artifact of the sandbox/build environment's clock, not a real problem with
Debian or the base image). Routed around it entirely rather than debugging
apt/GPG further: installed Node from the official prebuilt tarball
(`https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-arm64.tar.xz`,
extracted straight into `/usr/local`) instead of via `apt-get`, since that
path only depends on HTTPS, not Debian's apt keyring.

### What's actually in place now

- `Dockerfile.claude-cli` (repo root): extends
  `ghcr.io/open-webui/open-webui:main` with Node (tarball install) +
  `npm install -g @anthropic-ai/claude-code` (Linux-native binary, built
  inside the target platform).
- `docker-compose.override.yaml`: builds that Dockerfile instead of
  pulling the bare upstream image, tags it `open-webui-claude-cli:local`,
  and sets `CLAUDE_CONFIG_DIR=/app/backend/data/claude-cli-home`.
- Rebuilt and brought the container back up: `claude --version` inside it
  reports `2.1.197 (Claude Code)`, resolved via plain `claude` on `PATH`
  (`/usr/local/bin/claude`) -- so the Pipe's `CLAUDE_CLI_PATH` Valve can
  stay at its bare `claude` default, no per-instance override needed
  (confirmed the valve is unset/using default via `GET
  /api/v1/functions/id/claude_cli/valves` -> `{}`).
- `claude auth status` inside the rebuilt container currently reports
  `loggedIn: false` -- the one remaining step is a one-time `docker exec
  -it open-webui claude auth login`, which needs a real TTY and the user's
  own browser to complete, so it's not something this session can finish
  unattended. Once done, that login persists in the data volume across
  container restarts/rebuilds (as long as the volume itself isn't
  destroyed).

## 2026-08-21 — Build order step 3 complete, this time through the real Docker deployment

User ran `docker exec -it open-webui claude auth login` themselves (needed
a real TTY + their browser, not something this session could do).
`claude auth status` inside the container now reports `loggedIn: true,
authMethod: "claude.ai", subscriptionType: "pro"`.

**Live-verified through the actual containerized deployment** (not a
harness script, not the abandoned native process): `POST
http://localhost:3000/api/chat/completions` with `model: "claude_cli"`
streamed a real response end to end -- `open-webui` container -> `claude_cli`
Pipe -> real `claude` CLI subprocess (Node install baked into the image by
`Dockerfile.claude-cli`) -> JSONL translation -> SSE chunks out the same
HTTP API a browser client hits. This is the deployment shape that actually
matters (per the user's correction two entries back), not a workaround.

Build order step 3 is done, verified in the right environment this time.

## 2026-08-21 — MCP wiring hit `--permission-mode bypassPermissions` refusing to run as root

Set `MCP_SERVER_URL` on the live `claude_cli` function (`http://host.docker.internal:8931/mcp` --
confirmed reachable from inside the container first, `docker exec open-webui curl` against it
returned a real HTTP 406, not a connection failure, before trusting the URL). This activates
`_build_args`'s `--strict-mcp-config --tools "" --permission-mode bypassPermissions` combo. First
real chat through it failed: `--dangerously-skip-permissions cannot be used with root/sudo
privileges for security reasons`. Confirmed live: `docker exec open-webui whoami` -> `root` --
the `open-webui` image runs as root by default, and the CLI has a hard guardrail against
`bypassPermissions` while root (root + zero permission checks is a much bigger blast radius than
the one MCP server this session is actually scoped to).

Decided (with user sign-off, see next entries) to drop privileges for just the `claude` subprocess
rather than run the whole container non-root -- smaller blast radius, doesn't touch how the rest
of `open-webui` runs (writes to the mounted data volume, runtime `pip install`s for tool/function
frontmatter requirements, etc. all still need root).

## 2026-08-21 — `Dockerfile.claude-cli` gains a `claude-runner` user; `asyncio`'s `user=`/`group=` don't work under `uvloop`

Added `useradd --create-home --uid 1000 claude-runner` to `Dockerfile.claude-cli`. First
implementation used `asyncio.create_subprocess_exec(..., user=uid, group=gid)` (the documented,
normal way to do this since Python 3.9) -- failed live with `ValueError: unexpected kwargs: user,
group` inside `uvloop/loop.pyx`. **Live-verified, not assumed**: this container's event loop is
`uvloop`, and `uvloop`'s `subprocess_exec` doesn't implement the `user`/`group` kwargs the stdlib
asyncio loop does, even though both are nominally "asyncio."

Fixed by wrapping the subprocess argv with `setpriv --reuid=<uid> --regid=<gid> --clear-groups`
(from `util-linux`, already in the base image, no extra install) instead -- takes argv directly, so
the user's own message text never passes through a shell to be escaped. `claude_cli.py`'s
`_prepare_privilege_drop()` also `chown -R`s `CLAUDE_CONFIG_DIR` and a new `claude-cli-cwd`
directory (both under the persistent data volume) to `claude-runner` on every call, since the
files were originally created by root during the `claude auth login` step.

## 2026-08-21 — The long chase: non-root `claude -p` silently produced zero output, exit 0

This took the rest of the session. Every fix below was independently verified live and is
independently necessary for the sandbox to actually work -- but **none of them were the actual
cause** of the silent failure, which turned out to be something else entirely (final entry below).
Recording the false leads deliberately, not just the ending: each one is a real, confirmed
requirement for non-root `claude` in this container, and skipping any of them would break things
again even though none of them explains *this specific* symptom.

**Symptom, established first**: `claude -p "say hi"` as `claude-runner` (via `setpriv`, via raw
Python `os.setuid()`, and via a completely different throwaway user `nobody` with its own fresh
copied config -- ruled out `setpriv` itself, ruled out `claude-runner`'s specific setup) always
returned exit code 0 with **zero bytes on both stdout and stderr**, in under a second. As root,
the identical command reliably worked (confirmed repeatedly as a live control, including after
every fix below, to make sure nothing else had regressed).

1. **Missing XDG dirs** (`.cache`, `.config`, `.local/share`, `.local/state` under
   `claude-runner`'s home) -- created them; no change.
2. **`bubblewrap` + `socat` missing entirely.** Claude Code's own sandboxing docs
   (code.claude.com/docs/en/sandboxing, fetched live) confirm the Linux sandbox needs both.
   Installed via direct `.deb` download + `dpkg -i` from Debian's mirror (not `apt-get`: this
   sandboxed build environment's apt fails GPG verification on every Debian mirror --
   `At least one invalid signature was encountered` -- confirmed live to be this environment's
   clock reading 2026, past what the shipped archive keyring reads as valid; unrelated to Debian
   or the base image itself). `socat` needed `libwrap0` as a further dependency, chased down the
   same way. Bare `bwrap --ro-bind / / -- echo hello` then worked fine as `claude-runner` --
   but the actual symptom didn't change.
3. **`newuidmap`/`newgidmap` missing** (the `uidmap` package). `/etc/subuid` and `/etc/subgid`
   already had a `claude-runner` range (`useradd` provisions that automatically), but the binaries
   that consume it for a full unprivileged user-namespace setup weren't installed. `uidmap` needed
   `libsubid4` as a further dependency. Installed; symptom didn't change.
4. **`sandbox.enableWeakerNestedSandbox`.** Found via Claude Code's own docs (fetched live, both
   the general sandboxing page and settings-reference): "Bubblewrap fails to start inside a
   container: in an unprivileged container, bubblewrap cannot mount a fresh `/proc` filesystem. Set
   `enableWeakerNestedSandbox` to `true`..." -- describes this exact scenario (`open-webui`'s
   container is itself already unprivileged, no `--privileged`, no extra `SYS_ADMIN`). Set
   `{"sandbox": {"enableWeakerNestedSandbox": true}}` in `CLAUDE_CONFIG_DIR/settings.json`.
   Verified via `strace` (see below) that this exact path is genuinely what the CLI reads for a
   non-root run, not `$HOME/.claude/settings.json` -- confirmed live, not guessed, since both
   locations had been set at different points and only the `CLAUDE_CONFIG_DIR` one showed up as an
   `openat()` in the trace. Necessary, but still didn't fix the symptom on its own.
5. **Confirmed non-permission-related via `strace`** (installed the same direct-`.deb` way).
   `grep EPERM|EACCES` on the full trace: zero matches. The process resolves `api.anthropic.com`,
   completes a real TCP connect + TLS handshake to Anthropic's API, and even receives real
   encrypted application-data bytes back -- then a worker thread's `futex` wait times out, the
   process signals another thread, and the main thread calls `exit_group(0)`. **Only one `write()`
   to stdout/stderr in the entire trace, and it's from an unrelated child `git` process** -- the
   main process never even attempts to print anything. This ruled out a permission/capability
   denial and pointed at something failing silently deeper in the CLI's own logic, not the OS.

**The actual cause**: `claude --version` was `2.1.197` (whatever `npm install -g
@anthropic-ai/claude-code` unpinned resolved to during initial scoping). Upgrading to `2.1.239`
(latest at the time) changed nothing structurally, but changed *error reporting*: the identical
non-root invocation now printed `ENOSPC: no space left on device, mkdir '/tmp/claude-1000'`
instead of exiting silently. `docker system df` showed **20.99GB of fully unused build cache**
(0 active) from the session's own repeated `docker compose build` runs -- the Docker Desktop VM's
disk was completely full (`df -h /` inside the container: `100%`, `0` available). `docker builder
prune -f` freed it (22GB available after); the identical non-root `claude -p` call then worked
immediately, no other change.

So: **2.1.197 silently swallowed an out-of-disk-space error and exited 0 with no output at all**;
2.1.239 reports it properly. This session's own build activity was the actual proximate trigger
(filling the shared build-cache disk), but the CLI's silent failure mode on an old version is what
turned a one-line disk-space problem into hours of live debugging. Every fix in steps 1-4 above is
still genuinely required -- confirmed by testing the real MCP-configured path afterward, which
needs the sandbox to actually be functional, not just non-crashing.

**Made permanent, not just live-patched**: all of the above (bubblewrap/socat/libwrap0/uidmap/
libsubid4 `.deb` installs, `claude-code` pinned to `2.1.239` specifically rather than left
unpinned -- pinning avoids ever silently drifting back to a stale cached older install via
Docker's own layer cache, and avoids picking up an untested newer version automatically) got added
to `Dockerfile.claude-cli`, and `claude_cli.py`'s `_prepare_privilege_drop()` now writes
`CLAUDE_CONFIG_DIR/settings.json`'s `sandbox.enableWeakerNestedSandbox` itself (merged in, not
overwritten, in case anything else is ever in that file) rather than relying on the one-off manual
write done while debugging. Rebuilt the image with `--no-cache` from scratch and re-ran the full
live test (plain chat, then an actual MCP tool call -- `list_workflows` against the real
`ichirouganaim_mcp` server, which returned real workflow names) to confirm none of this depends on
anything left over in the previously-hand-patched running container.

Build order steps 3 (real subprocess) and the MCP-wiring detour are both done and verified live,
end to end, through the actual Docker deployment, from a clean image build.

## 2026-08-22 — Prep for replicating this on another machine

User asked for a `SETUP.md` to stand this up cleanly on a fresh server. Found and fixed two real
gaps before writing it:

- **Nothing was committed to git.** `Dockerfile.claude-cli`, `docker-compose.override.yaml`, and
  all of `docs/ichirouganaim-integration/` were untracked -- a fresh clone elsewhere would have had
  none of this. User is committing these themselves; not done in this session.
- **`Dockerfile.claude-cli` was arm64-only** (Node tarball URL and every `.deb` URL hardcoded to
  `arm64`), built and only ever tested on this Apple Silicon Mac. Most servers are amd64. Rewrote
  it to use buildx's automatic `TARGETARCH` build arg: Node.js needs "amd64" translated to "x64"
  (Debian's own archive already uses "amd64"/"arm64" natively, no translation needed for the
  `.deb` URLs). Verified the arm64 path still builds correctly (`--no-cache` rebuild, unchanged
  behavior). Attempted to cross-build-verify the amd64 path via
  `docker buildx build --platform linux/amd64` (build-only, not run -- no amd64 hardware here to
  actually execute it on) -- **had to abandon this**, not complete it: QEMU emulation made
  essentially zero progress (under 4s of CPU time) over 20+ minutes and was killed rather than left
  running indefinitely. The amd64 path is therefore genuinely unverified, not just "unrun" --
  logged honestly as such in `SETUP.md` rather than claiming a check that didn't finish.
- **`WEBUI_SECRET_KEY` was regenerating on every container recreation.** The auto-generate-if-unset
  path (`start.sh`) writes `/app/backend/.webui_secret_key` -- outside the persistent
  `open-webui:/app/backend/data` volume, so a fresh writable layer (every image rebuild) meant a
  fresh key, silently invalidating every existing login session each time. Not something this
  session had noticed before because API-key auth (what all the live verification used) is a plain
  DB lookup with no dependency on this key at all -- only browser session JWTs (and potentially
  encrypted Valves/OAuth data, per `OAUTH_CLIENT_INFO_ENCRYPTION_KEY`'s fallback to
  `WEBUI_SECRET_KEY`) are affected. Fixed by generating one fixed key (`openssl rand -base64 32`)
  and setting it directly in `docker-compose.override.yaml` rather than leaving it empty. Verified
  live: recreated the container, confirmed the "No WEBUI_SECRET_KEY... loading from file" startup
  log line no longer appears, and both the admin API key and the `claude` CLI's own auth still work
  unaffected.
- Deleted `docs/ichirouganaim-integration/claude-cli-bin/` (217MB) -- the host-side npm install
  from the abandoned native-detour testing. No longer used now that the CLI installs inside the
  container itself via `Dockerfile.claude-cli`; keeping it around served no purpose and isn't
  something a fresh clone should need to fetch or store.

## 2026-08-22 — Combined the API-key-bootstrap and Pipe-sync steps into `bootstrap.sh`

User asked whether `SETUP.md`'s steps 5 (mint an admin API key) and 6 (sync the Pipe) could be
scripted together, to remove the manual copy-paste of the key between them -- exactly the kind of
hand-off where a manual run is likely to go wrong.

Added two things:

- `bootstrap_admin_api_key.py` gained a safety fix: it used to unconditionally rotate the admin's
  API key on every run (`Users.update_user_api_key_by_id` deletes then recreates). Now checks
  `Users.get_user_api_key_by_id` first and reuses the existing key by default, only rotating with
  an explicit `--rotate` flag -- otherwise a second run of the combined script (e.g. re-running
  after an unrelated failure) would have silently invalidated a key something else might already
  be using.
- New `bootstrap.sh`: `docker cp`s the bootstrap script in, runs it, extracts `API_KEY=` from its
  output, immediately feeds that into `sync_pipe.py`. Live-verified twice against the running
  instance -- correctly reused the existing key both times (`REUSED_EXISTING_KEY=true`), and the
  Pipe sync succeeded (`Updated function "claude_cli".`) using the exact invocation now documented
  in `SETUP.md` (`bash docs/ichirouganaim-integration/bootstrap.sh`, not `./bootstrap.sh` --
  doesn't depend on the executable bit surviving a git commit/clone that hasn't happened yet).

`SETUP.md`'s steps 5-6 now lead with this script, with the manual UI-click-through-plus-`sync_pipe.py`
path kept as an explicit alternative for anyone who'd rather not run a script that logs into the
container.

## 2026-08-22 — Live capture of real `assistant`/`tool_use` and `user`/`tool_result` JSONL, before writing step 4

Per `scoping-tool-call-rendering.md`'s suggested order, captured a real MCP-tool-calling turn before
writing any step 4 translation code. Ran `claude -p "List the available workflows."` directly inside
the running `open-webui` container as `claude-runner` (same `setpriv`-wrapped invocation
`claude_cli.py` uses, same flags `_build_args()` builds), redirecting raw stdout to a file under
`CLAUDE_CONFIG_DIR` instead of going through the Pipe/HTTP layer, then `docker cp`'d it out and
deleted it from the container afterward (real MCP data, no reason to leave it in the persistent
volume). User approved spending subscription usage for this first.

**Confirmed live, replacing several "expect"/"verify this live" notes in the scoping docs**:

- **Tool name format**: `mcp__mcp__list_workflows` — exactly the `mcp__<server-key>__<tool>` pattern
  the scoping doc predicted from `_build_args()`'s `"mcp"` server key, not a paraphrase anymore. The
  `system`/`init` message's `tools` array also lists `mcp__mcp__get_record_graph_url` among the
  configured tools, confirming step 5's assumed tool name too.
- **`assistant`-type messages arrive one content-block-worth at a time, not cumulative.** A single
  turn that thinks then calls a tool produced *two separate* `assistant` JSONL lines — one with
  `message.content == [{type: "thinking", ...}]`, a second with `message.content == [{type: "tool_use",
  ...}]` — each emitted right as its content block's `content_block_stop` stream_event fires, not one
  message with both blocks. Step 4's `assistant` handler should treat `message.content` as
  "usually one block" and filter for `type == "tool_use"`, ignoring `thinking`/`text` blocks there
  (those already stream via `stream_event`/`content_block_delta`, handled by existing code).
- **The `tool_use` block's `input` is only guaranteed complete in the `assistant`-type line, not in
  the earlier `stream_event`/`content_block_start`.** For a no-argument tool like `list_workwows`
  input was `{}` at `content_block_start` already, but that's just this call happening to take no
  arguments — the block starts with `input: {}` and fills incrementally via
  `content_block_delta`/`input_json_delta` events in general, so a tool-name-only card could render
  early from `content_block_start`, but the final args must come from the `assistant` line's
  completed block once `content_block_stop` fires. There's also envelope-level `tool_use_meta`
  (sibling to `message`, e.g. `[{id, display_name: "List Workflows", server_display_name:
  "Ichirouganaim Authority API MCP Server"}]`) with human-readable names — not in the reference
  TS translator, but a nicer label source than the raw `mcp__mcp__...` string if the card wants one.
- **`tool_result.content` is a JSON-encoded string, not a structured object.** The `user`-type
  message's `message.content[]` entry is `{type: "tool_result", tool_use_id, content: "<JSON
  text>"}` — `content` needs its own `json.loads()` to get the actual result object (here,
  `{"result": [...]}`), it is not already parsed. Mirrored verbatim at the envelope's top level as
  `tool_use_result.content` (same string, redundant with the array entry). No `is_error` field was
  present on this success-case result; an error-case shape wasn't captured this round (only one tool
  call was made) — worth a second live capture later specifically for a failing tool call before
  assuming the same shape covers errors.
- `system`/`init` (`tools` array) and the final `result` line's extra fields (`total_cost_usd`,
  `modelUsage`, etc.) are both already silently ignored by `pipe()`'s `if/elif` chain today (no
  `else`, so no crash) — confirmed nothing new needs handling there for step 4 beyond `assistant`/
  `user`.

This is the real shape step 4's `__event_emitter__`/`structuredOutput.ts`-matching code gets written
against, not the paraphrased "expect tool names shaped like..." from the scoping doc.

## 2026-08-22 — Step 4 implemented: `output`-item emission for tool calls, plus a text-rendering gotcha found before writing any code

Before writing translation code, checked how the frontend actually consumes `message.output` --
found a real correctness trap the scoping doc hadn't flagged: `ContentRenderer.svelte:282`
(`{#if output?.length}`) renders **only** `StructuredOutputRenderer` once `output` is non-empty --
it does not also fall back to rendering the plain `content` string. Confirmed by reading
`middleware.py:4731-4759`: native tool-calling mirrors *every* text delta into a `message`-type item
inside `output` for exactly this reason, not just tool calls. Without doing the same in `claude_cli.py`,
the model's prose would have silently disappeared the moment a tool call happened in the same turn --
the bare-string SSE yields (which currently drive `message.content` directly) stop being displayed at
all once `output` is non-empty, per `Chat.svelte:2377-2385`'s `chatCompletionEventHandler`.

Implemented in `claude_cli.py`:

- `_ensure_message_item`/`_append_output_text` -- mirrors `middleware.py`'s own text-delta-into-`output`
  pattern (`utils/middleware.py:4732-4758`), called from the existing `text_delta` handler alongside
  (not instead of) the existing bare-string `yield`, so both channels carry the same text -- matches
  this app's own existing dual-channel architecture (HTTP SSE + websocket `__event_emitter__`), not a
  new pattern invented for this Pipe.
- `_append_tool_call`/`_append_tool_result` -- build `function_call`/`function_call_output` items from
  the `assistant`/`user` message types' `tool_use`/`tool_result` blocks, field-for-field matching
  `middleware.py:4930-4939,5117-5127`'s own shapes (`arguments` as a JSON string, `output` as
  `[{'type': 'input_text', 'text': ...}]` -- confirmed `input_text` specifically, not `output_text`,
  matches what native code emits there even though it reads oddly for a *result*).
- `_emit_output` -- calls `__event_emitter__({'type': 'chat:completion', 'data': {'output': output}})`
  and, separately, `Chats.upsert_message_to_chat_by_id_and_message_id(chat_id, message_id, {'output':
  output})` for persistence -- confirmed via reading `socket/main.py:946-1097`'s event-type dispatch
  that `chat:completion` has no built-in DB-persistence branch there (unlike `message`/`files`/`embeds`),
  so the Pipe doing its own persist call, exactly as the scoping doc says, is required, not optional.
  Added `__message_id__` to `pipe()`'s signature (confirmed `functions.py:267` already injects it
  automatically, same mechanism as `__chat_id__`) since persistence needs it.

**Live-verified, not just structurally read**: ran the real `Pipe().pipe()` coroutine directly inside
the running container (`docker exec`, imported the freshly-synced module directly) against a real chat
row created via `POST /api/v1/chats/new`, with a real MCP prompt (`"List the available workflows."`).
Confirmed:

- The final `output` array is exactly `[function_call, function_call_output, message]`, `call_id`
  matching between the two tool items, `status` correctly transitioning `in_progress` -> `completed`
  on the function_call once its result arrived, tool result text preserved as the same raw JSON string
  captured earlier.
- `GET /api/v1/chats/<id>` afterward shows the message really persisted with that same `output` shape,
  and `content` auto-backfilled from it (`Chats.upsert_message_to_chat_by_id_and_message_id`'s own
  `get_output_text` fallback, confirmed still firing).

**Browser-verified**: user opened the "step4-verify" chat (`4c018bee-9752-483f-8dec-7cf74edc2bd5`) at
`http://localhost:3000` -- no further Claude usage needed, since the message from the in-container test
above was already persisted. Confirmed the tool call renders as the same collapsible "View Result from
`mcp__mcp__list_workflows`" card native tool-calling produces, with Input/Output sections (Output showing
the pretty-printed JSON `{"result": [...]}`), and the assistant's prose renders normally *below* the
card -- not swallowed, confirming the `ContentRenderer.svelte`/`message`-item concern above was correctly
handled. Step 4 (tool-call `output`-item emission) is done, live-verified end to end including the
browser render, satisfying the project's "run the dev server and look at it" consistency requirement.

## 2026-08-22 — Step 5: graph-url.ts / GraphCard / GraphModal, live-verified through a real dev-mode frontend build

Read the reference repo's `lib/graph-url.ts`, `components/GraphCard.tsx`, `components/GraphModal.tsx`
before writing anything, per Part 2's "Read first" list. Confirmed a real live-captured
`get_record_graph_url` result this session (see the earlier 2026-08-22 entry's follow-up capture below)
matches the reference docstring's own documented "claude-cli provider" shape exactly:
`'{"result":"<url>"}'` as a JSON-encoded string, no `structuredContent`/`content[]` envelope --
`claude_cli.py`'s own `_append_tool_result` only ever forwards the array item's raw `content` field, so
that's the only shape `extractGraphUrl` actually needs to handle for this integration; the reference's
other branches (`structuredContent`, `content[]`) are kept as cheap defensive fallbacks, not because
they're reachable today.

**Fresh live capture** (approved as part of starting step 5): ran `claude -p "Look for any existing
recorded events already in the system... call get_record_graph_url for it..."` directly in-container.
It found a real event (from the earlier deed-entry test session) and called `get_record_graph_url` for
real -- confirmed tool name `mcp__mcp__get_record_graph_url`, input `{"record_id": "<uuid>"}`, result
`'{"result":"http://127.0.0.1:1246/records/<id>/graph-view/"}'`. Cheaper than re-running a full
deed-entry workflow from scratch since a record already existed from prior testing.

**New files**, matching this fork's own existing conventions rather than porting the reference's React
markup verbatim (per the consistency requirement):

- `src/lib/utils/graph-url.ts` -- `isGraphUrlTool`/`extractGraphUrl`, ported logic per above.
- `src/lib/components/common/GraphCard.svelte` -- a small rounded-full pill button ("View Graph" +
  `Merge` icon, the closest existing icon to a node-link graph glyph -- this fork has no literal
  network/graph icon), modeled on `Citations.svelte`'s own source-toggle pill
  (`text-xs ... px-3.5 h-8 rounded-full ... border border-gray-50 dark:border-gray-850/30`), not the
  reference's bigger bordered-box card -- this fork's own closest existing "compact clickable summary
  inline in a message" precedent.
- `src/lib/components/common/GraphModal.svelte` -- `Modal size="lg"`, header matching
  `CitationsModal.svelte`/`CitationModal.svelte`'s exact layout (title/URL left, `XMark` close button
  right), body reuses `FullHeightIframe.svelte` (the same iframe primitive `ToolCallDisplay.svelte`'s
  own embeds-mode branch already uses, same `$settings?.iframeSandboxAllow*` toggles) inside a
  `h-[70vh]` wrapper rather than hand-rolling a new `<iframe>`/sandbox policy.
- `ToolCallDisplay.svelte` -- new top-level `{#if !grouped && graphUrl}` branch (gated the same way the
  existing embeds-mode branch is), computed reactively from the component's own already-decoded `result`
  string; falls through to the generic block on any tool-name mismatch, in-progress call, or failed
  extraction -- never renders nothing.

**Live-verified through a real dev-mode frontend build**, not just read: the running Docker container
serves the stock upstream frontend bundle (not built from this checkout), so a real browser check needed
an actual Vite dev server built from this checkout's source. Set up per user approval:

- `docker-compose.override.yaml` gained a `ports: ['8080:8080']` entry (additive to base
  `docker-compose.yaml`'s `3000:8080` -- compose appends list fields across `-f` files by default,
  confirmed via `docker compose config` before restarting) -- `src/lib/constants.ts` hardcodes dev-mode
  API calls to `http://<hostname>:8080`, so this exposes the container's real port directly rather than
  needing a native backend (kept Docker-only per this project's own earlier correction, see the
  2026-08-21 "Reverted the native detour" entry).
- `npm install` needed `--engine-strict=false` -- this repo's own `.npmrc` sets `engine-strict=true`,
  and several transitive deps (`eslint-visitor-keys@5.0.1`, `undici@7.28.0`, `yargs@18.0.0`) require a
  newer Node than this host's `v20.17.0`. Not a code change, just a one-off install-time flag; didn't
  touch `.npmrc` itself.
- `node_modules/.bin/vite dev --host` (not `npm run dev`, which chains `pyodide:fetch` first -- an
  unrelated, unnecessary download for this check) served real dev-mode Svelte on `:5173`.
- Needed a `get_record_graph_url` call in a chat's history to look at, without spending further Claude
  usage: rather than hand-writing fake output JSON, replayed the real captured JSONL above through
  `claude_cli.py`'s actual `_append_tool_call`/`_append_tool_result`/`_append_output_text` methods
  in-container (same code, not reimplemented), producing the exact `output` array a live run would have,
  then persisted it directly via `Chats.upsert_message_to_chat_by_id_and_message_id` into a fresh test
  chat (`71dc3770-e797-4000-bbb1-ae443bb6e0e7`, "step5-verify-graph-card") -- this replay also happened
  to include the capture's earlier `events_list` call, which turned out useful: it gave the browser
  check a second, non-graph tool call in the same message to confirm against (see below).
- Drove a headless Chromium against `localhost:5173` with the `playwright` npm package (no `chromium-cli`
  skill available in this environment) -- `localStorage.setItem('token', <admin API key>)` before
  navigating worked for auth (the same Bearer-token dependency backs both the API-key-authenticated curl
  calls used all session and the SPA's own session check).

**Confirmed by screenshot** (`GET /c/71dc3770-...` in the dev-mode frontend):

- The `events_list` call rendered as the ordinary collapsible "View Result from `mcp__mcp__events_list`"
  row -- confirming `isGraphUrlTool` correctly does *not* match an unrelated tool.
- The `get_record_graph_url` call rendered as the new compact "View Graph" pill instead of a generic row
  -- confirming the branch fires correctly for the one tool it should.
- The assistant's prose text rendered normally before/after/between both tool calls -- confirming the
  step-4 `message`-item mirroring still works correctly once step 5's branch is layered on top.
- Clicking "View Graph" opened the modal: header showing the real URL, close button, and a real
  `<iframe>` element pointed at it -- confirmed via DOM query (`iframe` count went from 0 to 1) and a
  screenshot of the open modal.

**One known gap, not a defect**: the iframe's body rendered blank in the screenshot, because
`http://127.0.0.1:1246/...` (the graph-view server from the *original* live deed-entry session's local
network) isn't reachable from this test environment -- expected, unrelated to `GraphModal`/`FullHeightIframe`
correctness. A page console error (`Failed to read the 'localStorage' property... sandboxed and lacks the
'allow-same-origin' flag`) came from *inside* that unreachable iframe attempting a same-origin check under
the default (non-same-origin) sandbox policy -- also expected, and actually a good sign: it confirms the
sandbox restriction is genuinely being enforced, not a bug to fix.

Step 5 is done, live-verified through a real rendered browser page (not just structurally), satisfying
the same "run the dev server and look at it" bar step 4 was held to.

**Left running / in place after this session, cleanup optional**: the Vite dev server on `:5173`
(`node_modules/.bin/vite dev --host`) and the `71dc3770-...` ("step5-verify-graph-card") test chat --
both local-dev-only and harmless to leave, but not required to keep the feature itself working (the
feature only needs the real image rebuilt with these source changes for actual production use through
the normal `:3000` Docker path). The `8080:8080` port mapping this session temporarily added to
`docker-compose.override.yaml` to make this dev-server check possible was removed again afterward (see
the next entry) -- it was explicitly local-dev-only from the start, not part of the actual deployment.

## 2026-08-22 — Frontend build stage runs out of memory; moving the build to a different machine instead of raising Docker Desktop's memory

Tried to close the loop on step 5 by actually rebuilding the real `:3000` Docker image with
`Dockerfile.claude-cli`'s new frontend-build stage (added this session, see the step 5 entry above) --
the running container still served the stock upstream frontend bundle, which doesn't include
`GraphCard`/`GraphModal`/`graph-url.ts` at all.

**First build attempt failed**, live: `docker compose build` died during `RUN npm run build` inside the
`frontend-build` stage with `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of
memory` -- V8's own graceful heap-limit error, not an OS-level kill. `docker info` showed Docker
Desktop's VM has only 3.827GiB total memory allocated; the build's heap climbed to ~1.95GB before dying,
still mid-build (repeated "Mark-Compact" GC passes trying and failing to free space), not a case of it
finishing and then running low.

**Diagnostic step 1** (user's idea, worth trying since it's free): stopped every other container sharing
that Docker Desktop VM (`ollama`, `ichirouganaim-django`, `ichirouganaim-db` -- confirmed via `docker ps`
these genuinely do run in Docker, correcting an earlier wrong assumption in this same conversation that
`ichirouganaim` was host-native; it's a separate `docker-compose` project reachable via
`host.docker.internal`) to free up their combined ~715MB of usage, then retried. **No change** -- died
the same way, actually *faster* (52s vs 112s). This ruled out sibling-container memory contention as the
cause: V8's own auto-detected heap ceiling is set from total available memory at process start, not
current momentary usage, so freeing memory elsewhere in the VM didn't raise it.

**Diagnostic step 2**: added `ENV NODE_OPTIONS="--max-old-space-size=3072"` to the `frontend-build`
stage (forcing a higher heap ceiling instead of relying on V8's conservative auto-detection) and retried.
This got meaningfully further (133s vs 52s of progress) -- confirming the forced ceiling helped -- but
then died differently: `npm error signal SIGKILL`, `failed to solve: ResourceExhausted: ... cannot
allocate memory`. This is the kernel itself killing the process for real memory exhaustion, not V8's own
graceful error. That's the conclusive signal: the surrounding VM genuinely does not have enough real
memory for this build, independent of how conservatively or aggressively V8's heap is configured -- no
further Dockerfile-level tuning can fix an actual physical/VM ceiling. Kept the `NODE_OPTIONS` line in
`Dockerfile.claude-cli` since it did measurably help and should still be useful on a machine with enough
underlying memory to make it matter.

**Decision**: user is not comfortable raising Docker Desktop's memory allocation on this machine.
Instead, this build (and the eventual real deployment) moves to a separate, more capable machine (a Mac
Studio, user's own hardware) -- same CPU architecture (Apple Silicon / arm64) as this dev machine, so the
already-verified arm64 build path applies directly with no need to touch the unverified amd64 path.
`docker-compose.override.yaml`'s temporary `8080:8080` port mapping (added only to let a local `vite dev`
frontend reach this instance for the earlier dev-server-based verification) was removed again -- it was
never part of the real deployment, only scaffolding for that one check.

**Documented for the target machine, not fixed here**: `SETUP.md`'s Prerequisites section now has an
explicit memory bullet describing both failure signatures above (the graceful V8 heap error and the hard
`SIGKILL`) and what to do if either shows up there too -- most likely a non-issue on a Mac Studio-class
machine with generous RAM, but worth having documented rather than rediscovering live again on a second
machine. `SETUP.md`'s step 3 and troubleshooting table were updated to match; see that file directly
rather than duplicating the wording here.
