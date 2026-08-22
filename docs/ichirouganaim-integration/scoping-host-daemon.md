# Scoping: custom host-side `claude` daemon (alternative to in-container CLI)

**Status: scoped, not built.** This is an optional alternative architecture,
not a plan to replace what's currently working. The in-container approach
(`Dockerfile.claude-cli`, `claude_cli.py`'s local subprocess spawn) is
fully built, live-verified, and documented in
[`SETUP.md`](SETUP.md)/[`decisions.md`](decisions.md). Nothing here
changes that unless a decision is made to switch.

## Why this exists

Conversation-driven: after getting the in-container `claude` CLI working
(non-root, sandboxed, MCP-wired), the question came up — why does `claude`
run *inside* the `open-webui` container at all, instead of on the host,
with the container just contacting it? Answered informally in chat; this
document scopes what actually building that second option would take.

**The real motivation for considering it**: almost all of the complexity in
`Dockerfile.claude-cli` and `claude_cli.py`'s `_prepare_privilege_drop()`
exists only because Claude Code sandboxes itself when it detects it's
running non-root *inside an already-unprivileged container* —
`bubblewrap`, `socat`, `uidmap`, `enableWeakerNestedSandbox`, the
`claude-runner` user, the `setpriv` wrapping. None of that is needed for a
plain host process running as a normal (non-root) user on a real Linux
host — Claude Code's own sandbox works normally there. A host-side daemon
would sidestep that whole category of problem entirely, at the cost of
introducing a new one (see "Recommendation" at the end).

## Non-goals for this document

- **Not** scoping the SSH-based bridge mentioned in conversation as the
  lower-effort alternative — this document is specifically the "custom
  daemon" option, per what was asked for.
- **Not** a remote/multi-host daemon design (TLS, network-exposed auth
  tokens). Scoped for the daemon co-located on the same physical/VM host
  as the Docker engine running `open-webui` — the only case `SETUP.md`
  currently targets.
- **Not** multi-tenant (multiple Claude.ai accounts/orgs routed by the
  daemon). This integration is single-account by design already, and nothing
  here changes that.
- **Not** a decision to actually build this. Ends with a recommendation,
  not a "start here" build order, unlike Part 1/2 of the original scoping
  doc — build order only makes sense once there's a decision to proceed.

## What changes and what doesn't

**Doesn't change**: `claude_cli.py`'s `stream_event`/`assistant`/`user`/
`result` JSONL-translation logic (the bulk of `pipe()`) — it already just
reads lines and yields text; it doesn't care whether those lines came from
a local pipe or a socket.

**Changes**: how the subprocess gets invoked. Today: `pipe()` builds argv
and calls `asyncio.create_subprocess_exec` locally (wrapped in `setpriv`
for the privilege drop). With a daemon: `pipe()` instead opens a
connection to the daemon and reads its streamed response — the daemon does
the actual `subprocess_exec` call, on the host.

**Could be removed, if this became the primary path**: everything in
`Dockerfile.claude-cli` past the base `FROM` — Node.js, `claude-code`,
`bubblewrap`/`socat`/`uidmap`, `claude-runner`. The container could go back
to the stock upstream `ghcr.io/open-webui/open-webui:main` image. This is
the real payoff of this design, not a side effect.

**Confirmed, not assumed**: the container side needs zero new dependencies
to talk to a Unix-socket daemon — `aiohttp==3.13.5` is already a pinned
dependency (`pyproject.toml:25`), and `aiohttp` has built-in Unix-domain-
socket support (`aiohttp.UnixConnector`). No Dockerfile change needed for
the client side of this at all.

## Architecture: transport choice

Two real options, both workable:

| | TCP + token auth | Unix domain socket |
|---|---|---|
| Access control | A bearer token the daemon checks per-request — you build and maintain this | Filesystem permissions on the socket file — the OS already does this |
| Network exposure | A port bound on the host, reachable by whatever can route to it (careful with `0.0.0.0` vs a specific interface — see below) | None. No port, not reachable over any network at all |
| Portability | Slightly more general (daemon and container don't strictly need to be co-located) | Ties daemon and container to the same host (fine — that's this doc's actual scenario) |
| Setup | Daemon binds a port; container gets a URL + token via Valve/env | Bind-mount the socket's directory into the container; container gets a path |

**Recommendation: Unix domain socket.** This deployment is single-host by
design (per `SETUP.md`), so the TCP option's only real advantage
(location-independence) doesn't apply here, while its cost (build and
operate a token-auth scheme yourself, and mind the host's network binding
carefully — a service on `0.0.0.0:PORT` is reachable by anything that can
reach the host at all, not just the one container that should be talking
to it) is real. A Unix socket has no such exposure: nothing outside the
host's filesystem can reach it at all, and "what can reach it" is exactly
"what has the container's bind mount," which we control directly in
`docker-compose.override.yaml`.

**Operational detail that matters**: bind-mount the socket's *containing
directory*, not the socket file itself. A daemon restart typically
unlinks and recreates its socket file; if only the file were bind-mounted,
the container would keep looking at a stale/broken mount after a daemon
restart. Mounting the directory (e.g. `/var/run/claude-daemon/`) means the
container always sees whatever socket currently exists there.

## Wire protocol

**Request** (one per chat turn, from the Pipe):

```json
{"message": "...", "chat_id": "...", "model": null}
```

Deliberately **not** included: `mcp_config`, `tools`, `permission_mode`.
See "Security model" — those are fixed by the daemon's own policy, not
supplied by the caller.

**Response**: the daemon proxies `claude`'s own `--output-format
stream-json` output back over the connection line-by-line, as it's
produced — not buffered, not re-encoded. `claude_cli.py`'s existing
per-line JSON parsing loop barely changes: it already reads one JSON
object per line and translates it; the only change is *where* the lines
come from (a socket read loop instead of `proc.stdout`).

**Session/resume state**: the daemon should own the `chat_id ->
claude-session-id` mapping itself (a small file, mirroring today's
`sessions.json` — same idea, just relocated to wherever the daemon keeps
its own state on the host), rather than the Pipe passing a
`resume_session_id` it tracked itself. Simpler split of responsibility:
the daemon is the only thing that ever actually invokes `claude`, so it's
the natural owner of session continuity too.

## Security model — the part that matters most here

This is the one place a daemon design can go quietly, badly wrong, so it's
worth being explicit: **the daemon runs with the access of whatever host
user starts it — not the tightly-scoped, `--tools ""`-restricted sandbox
the container gives it today.** If the daemon let the calling container
dictate the full `claude` argument set (its own `--mcp-config`, `--tools`,
`--permission-mode`), then a bug in the Pipe — or a compromised container —
could ask the host daemon to run `claude` with full tool access and
bypassed permissions directly against the host filesystem. That's a much
larger blast radius than anything possible today.

**The daemon must enforce its own fixed policy, unconditionally**:

- Its own hardcoded (or daemon-config-file-controlled, not
  request-controlled) `--mcp-config` pointing at the one approved MCP
  server.
- Always `--strict-mcp-config --tools "" --permission-mode
  bypassPermissions` — same pairing reasoning as today, just enforced
  server-side instead of Pipe-side.
- The request body should only ever be able to influence the *message
  text*, *which chat's session to resume*, and maybe a *model override* —
  nothing that touches tool/permission/MCP configuration.

**Other things worth building in, not just noting**:

- A concurrency cap (a configurable max simultaneous `claude` invocations)
  — this executes against a real subscription; an unbounded fan-out from a
  bug is a real cost, not just a resource-exhaustion concern.
- Run the daemon itself as a **dedicated, non-privileged host user** —
  separate from your own interactive login and separate from root. Same
  principle as `claude-runner` inside the container, just at the host-user-
  account level (`useradd`/equivalent) instead of container-user level.
  This also keeps its `claude auth login` session cleanly separated from
  anyone's personal interactive `claude` usage on the same machine.
- Minimal logging of *what* was asked (timestamps, chat ids, maybe message
  length) without necessarily logging full message content, for basic
  auditability without turning the daemon into a transcript store.

## Process lifecycle / installation

The daemon needs to be a real, persistent service — not something started
by hand and forgotten:

- **Linux (the realistic server target)**: a `systemd` unit — auto-start on
  boot, auto-restart on crash (`Restart=on-failure`).
- **macOS (dev-machine convenience)**: a `launchd` plist, mirroring the
  systemd unit's auto-restart behavior (`KeepAlive`).
- Both need the dedicated non-privileged user from the security section
  above provisioned first.

## Rough build plan (not executed — scoping only)

If a decision is made to proceed:

1. Write the daemon: a small standalone Python service (keep dependencies
   minimal, given "custom" was the ask — stdlib `asyncio` +
   `asyncio.start_unix_server` is plausibly enough; no need to pull in a
   full web framework for a single-purpose line-oriented protocol like
   this). Implements the protocol above: accepts a connection, spawns
   `claude` with its own fixed flags + the caller's message, streams
   stdout back line by line, tracks/persists session-resume state,
   enforces the concurrency cap.
2. Add a Valve to `claude_cli.py` (e.g. `DAEMON_SOCKET_PATH`, empty by
   default) and branch `pipe()`: empty → today's local-subprocess path
   unchanged; set → connect via `aiohttp.UnixConnector` and relay the
   daemon's stream through the same JSONL-translation logic. Keeps both
   modes available side by side, switchable per-deployment, rather than a
   hard cutover that risks the already-working path.
3. Add the socket-directory bind mount to `docker-compose.override.yaml`
   (only relevant once daemon mode is actually in use).
4. Write a `SETUP-host-daemon.md` (or a clearly-marked alternate section in
   the existing `SETUP.md`) covering: host-level Node/`claude-code` install,
   the dedicated host user, `claude auth login` done there, the
   systemd/launchd service install, socket directory permissions.
5. Live-verify: streaming still works end to end; confirm the daemon
   actually rejects/ignores any attempt from the request body to override
   `--tools`/`--mcp-config`/`--permission-mode` (don't just assume the
   fixed-policy code is correct — test it the same "verify, don't assume"
   way this whole integration has been built); session resume works;
   concurrent requests from different chats don't cross-contaminate
   sessions.
6. Decide whether this becomes the default going forward or stays optional
   — and if default, simplify `Dockerfile.claude-cli` back down (drop
   everything past the base image).

## Recommendation

Worth being direct about the actual tradeoff, not just describing it:

**The in-container approach already works, is live-verified, and is
fully reproducible via `SETUP.md` with nothing beyond Docker required on
the target machine.** That reproducibility is a real, already-banked
property — `SETUP.md` was written specifically so a fresh server needs
*only* Docker installed, nothing else. A host-side daemon **reintroduces
exactly the host-dependency problem `SETUP.md` was written to eliminate**:
a new deployment target would now also need Node, `claude-code`, a
dedicated OS user, and a systemd/launchd service installed and managed
*outside* Docker — unless that setup gets its own equally rigorous
packaging and documentation, which is real, additional work, not a
byproduct of building the daemon itself.

The daemon's genuine advantages are real but narrower than "avoids the
sandbox complexity" alone: that complexity is a one-time cost that's
already paid, pinned, and working in `Dockerfile.claude-cli` today. Where
a daemon would actually pay for itself is a scenario not yet in play here
— e.g. multiple `open-webui` deployments/containers sharing one
`claude auth login` instead of each needing its own. If that becomes a
real need, this document is the starting point. Absent that, this reads as
an interesting alternative worth having scoped, not a clear improvement
over what's already built and verified.
