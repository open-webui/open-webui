# Setup: claude-cli model on a fresh machine (e.g. a server)

Step-by-step instructions to stand up this fork with the `claude_cli`
model/Pipe working, from nothing, on any Docker host — a fresh clone on a
server, not just this dev machine. For *why* things are built this way, see
[`decisions.md`](decisions.md) and
[`scoping-claude-cli-and-graph-modal.md`](scoping-claude-cli-and-graph-modal.md).
This file is the "what to actually run," not the reasoning.

## What you end up with

`open-webui`, running in Docker, with an extra model in the dropdown called
`claude_cli` that chats through a real `claude` CLI subprocess running
*inside* that same container, authenticated with a Claude.ai subscription
login (not a separate `ANTHROPIC_API_KEY`), optionally with tool access to
one configured MCP server.

## Prerequisites

- Docker Engine + Docker Compose v2 (the `docker compose` subcommand, not
  the older standalone `docker-compose`).
- A Claude.ai account that can log into the `claude` CLI (`claude auth
  login`'s normal browser flow). Any plan that supports Claude Code works —
  this integration uses that login directly, not per-token API billing.
- An amd64 or arm64 Linux Docker host, or macOS with Docker Desktop.
  **The arm64 path (Apple Silicon) is fully verified end-to-end.** The
  amd64 path is written to the same logic (`Dockerfile.claude-cli` resolves
  package/binary architecture automatically from Docker's own
  `TARGETARCH`) but is **unverified** — a `docker buildx build --platform
  linux/amd64` cross-build was attempted to at least check it structurally,
  but QEMU emulation never made real progress in this sandboxed session
  (killed after 20+ minutes stuck at effectively zero CPU time) and had to
  be abandoned rather than left claiming a check that didn't actually
  finish. No amd64 hardware was available either. The exact `.deb`/Node.js
  versions pinned in the Dockerfile are known-good for arm64 and Debian
  publishes the same versions for amd64 from the same source, so it's
  *likely* to just work — but budget time to debug it on first real amd64
  use, and please fold whatever you find back into this file and
  `decisions.md`.
- **Real free disk space — at least 10-15GB, ideally more.** This isn't a
  throwaway warning: an out-of-disk-space condition during this exact setup
  once caused the `claude` CLI to silently produce zero output with no
  error at all (fixed now by a version pin — see
  [`decisions.md`](decisions.md) — but budget the space anyway; a good
  chunk of a slow, several-hour debugging session traced back to this).
  Run `docker system df` before starting, and periodically
  `docker builder prune -f` (safe — only removes unused build cache) if it
  creeps back up after repeated rebuilds.
- **At least ~6GB of memory available to Docker itself, ideally more —
  this is new as of the step 4/5 work (tool-call rendering + the graph-url
  card) and matters more than it sounds like it should.** `Dockerfile.claude-cli`
  now includes its own frontend-build stage (`npm run build`, i.e. a real
  Vite/Rollup production build of the whole Svelte app, needed so the
  container's frontend actually includes this integration's own UI changes
  — `GraphCard.svelte`/`GraphModal.svelte`/`graph-url.ts` — instead of just
  the stock upstream bundle `ghcr.io/open-webui/open-webui:main` ships).
  That build step is memory-hungry. **Live-verified, not theoretical**: on a
  Docker Desktop VM capped at 3.8GB total, this build reliably failed —
  first with Node's own graceful `FATAL ERROR: ... JavaScript heap out of
  memory` (V8 hit its auto-detected heap ceiling, still mid-build, not yet
  done), then, after forcing a larger heap via `NODE_OPTIONS=--max-old-space-size=3072`
  (already set in `Dockerfile.claude-cli`'s frontend-build stage — don't
  remove it, it helped it progress further before still dying), with a hard
  `SIGKILL`/`cannot allocate memory` from the kernel itself — the second
  failure mode is the one that actually proves the ceiling is too low, not
  just conservatively auto-detected: no amount of build-flag tuning fixes a
  VM that plainly doesn't have the memory. See decisions.md's 2026-08-22
  "Frontend build stage runs out of memory" entry for the full blow-by-blow
  of both failure modes and why the workaround of stopping other running
  containers didn't help either (the ceiling is the whole VM's allocation,
  not contention from sibling containers). A machine with generous RAM
  (e.g. a Mac Studio) shouldn't hit this at all — Docker Desktop's default
  memory allocation on a high-RAM host is normally already well above this
  ceiling — but if the build fails with either of the two symptoms above,
  this is the cause, and the fix is giving Docker more memory (Docker
  Desktop: Settings → Resources → Memory; Docker Engine on Linux isn't
  capped the same way and shouldn't need this at all).

## 1. Get the files onto the machine

Clone this repo. Confirm these specific files are present — they are
**not** part of upstream open-webui, and depending on how/when this repo
was forked from your own history, may not have been committed yet:

```
Dockerfile.claude-cli
docker-compose.override.yaml
docs/ichirouganaim-integration/claude_cli.py
docs/ichirouganaim-integration/sync_pipe.py
docs/ichirouganaim-integration/bootstrap_admin_api_key.py
docs/ichirouganaim-integration/bootstrap.sh
```

The scripts referenced later, in step 8/8b and "Long-term operation," are
optional but worth having too — not required for a working setup, only
for wiring up MCP access and ongoing maintenance once it's been running a
while:

```
docs/ichirouganaim-integration/configure_mcp.sh
docs/ichirouganaim-integration/register_mcp_tool_server.sh
docs/ichirouganaim-integration/check_claude_auth.sh
docs/ichirouganaim-integration/backup_data_volume.sh
docs/ichirouganaim-integration/check_claude_code_version.sh
docs/ichirouganaim-integration/docker_disk_cleanup.sh
docs/ichirouganaim-integration/concurrency_test.sh
```

If any are missing, they need to be copied over or committed from
wherever this fork was originally built — there's no way to regenerate
them from the base open-webui repo alone.

**As of the step 4/5 work, the frontend itself also matters, not just these
integration-specific files.** `Dockerfile.claude-cli` now builds the whole
Svelte frontend from this checkout's own `src/` (see step 3) rather than
only extending the upstream image's pre-built bundle — so a full, normal
`git clone` of this fork (not a partial/sparse checkout) is required, same
as it would be for building open-webui's own root `Dockerfile`. Nothing
extra to list here for that part specifically (it's just "the whole repo,"
not a special file set) — this note exists so a partial copy of only the
files above (which was a reasonable thing to do before this fork had a
frontend-build step at all) doesn't quietly produce a container with a
frontend build failure or a stale/incomplete UI.

## 2. Configure `docker-compose.override.yaml` for this deployment

The one in this repo already has the required pieces; review each before
reusing it on a new machine:

```yaml
services:
  open-webui:
    build:
      context: .
      dockerfile: Dockerfile.claude-cli
    image: open-webui-claude-cli:local
    depends_on: !reset []
    environment:
      WEBUI_SECRET_KEY: '<a fixed secret, see below>'
      CLAUDE_CONFIG_DIR: /app/backend/data/claude-cli-home
    extra_hosts:
      - host.docker.internal:host-gateway
```

- **`build`/`image`** — required. Without this, `docker compose` pulls the
  bare upstream image with no `claude` CLI, no Node, none of it.
- **`WEBUI_SECRET_KEY`** — **generate your own** with
  `openssl rand -base64 32`; don't reuse the value currently checked into
  this repo's copy of the file (if it's been committed anywhere, treat it
  as already-compromised and rotate it). Setting a fixed value here matters
  for reasons that aren't obvious: left unset, open-webui auto-generates
  one on first boot and writes it to a file *inside the container's own
  writable layer*, not the persistent data volume — so it silently
  regenerates on every container recreation (every rebuild), invalidating
  every existing login session each time. A fixed value avoids that.
- **`CLAUDE_CONFIG_DIR`** — required, leave as-is. Redirects the `claude`
  CLI's own credential/session storage into the already-persistent
  `open-webui:/app/backend/data` volume, so `claude auth login` (step 6)
  only has to happen once per deployment, not on every restart.
- **`extra_hosts: host.docker.internal:host-gateway`** — required if
  anything the container needs to reach (an MCP server, Ollama, etc.) runs
  on the same host machine outside Docker. Works the same way on native
  Linux Docker Engine (20.10+) as it does on Docker Desktop — this isn't a
  Mac-only convenience despite the name.
- Anything else in this repo's copy of the file (`OLLAMA_BASE_URL`,
  `RAG_EMBEDDING_ENGINE`, `RAG_EMBEDDING_MODEL`) is unrelated to the
  `claude_cli` integration — leftover local configuration for this dev
  machine's Ollama setup. Remove or adjust for the target server; none of
  it is required for `claude_cli` to work.

## 3. Build and start

```bash
docker compose -f docker-compose.yaml -f docker-compose.override.yaml build
docker compose -f docker-compose.yaml -f docker-compose.override.yaml up -d
```

The build now has two real phases, in order:

1. **Frontend build** (`frontend-build` stage, `node:22-alpine3.20`): a
   normal `npm ci --force && npm run build` of this checkout's own Svelte
   frontend — the same recipe the root `Dockerfile` uses for the official
   image, just producing a bundle that includes this integration's own
   `GraphCard`/`GraphModal`/graph-url-card UI changes instead of the stock
   one. This is the slow, memory-hungry phase — see the Prerequisites
   section above if it fails with an out-of-memory error. Expect several
   minutes here alone on a healthy machine, not "a couple of minutes"
   total like earlier versions of this doc said (that estimate predates
   this stage existing at all).
2. **Backend/CLI layer** (extends `ghcr.io/open-webui/open-webui:main`):
   installs Node.js (again, separately — this one's for running the
   `claude` CLI at container runtime, unrelated to the frontend build
   above), the `claude` CLI itself (pinned to a specific version — see
   [`decisions.md`](decisions.md) for why an unpinned "latest" bit us
   once), the sandboxing dependencies (`bubblewrap`, `socat`, `uidmap` and
   their own dependencies) needed for the CLI to run as a non-root user
   later, and finally overlays the frontend build's output from phase 1
   on top of the base image's own stock bundle.

Total time varies a lot by machine and whether Docker's build cache is
warm; budget more than the old "a couple of minutes" estimate, especially
on a clean build.

Confirm it's up:

```bash
curl http://localhost:3000/health   # {"status":true}
```

(Port 3000 is the default from the base `docker-compose.yaml`; override
with `OPEN_WEBUI_PORT` if needed.)

## 4. Create your admin account

Open `http://<host>:3000` in a browser and sign up. **The first account
created becomes admin automatically** — this only applies to the very
first signup on a fresh instance.

## 5-6. Get an admin API key, then sync the `claude_cli` Pipe function

**Recommended — one script does both:**

```bash
bash docs/ichirouganaim-integration/bootstrap.sh
```

Mints (or, on a re-run, reuses — see below) an admin API key, then
immediately uses it to sync the Pipe. This is the combined form
specifically so there's no manual copy-paste of the key between the two
steps — that hand-off is the easiest place for a manual run to go wrong
(stale key from a previous attempt, wrong container name, etc). Requires
the admin account from step 4 to already exist first. Override
`OPEN_WEBUI_CONTAINER` / `OPEN_WEBUI_BASE_URL` env vars if they differ from
the defaults (`open-webui` / `http://localhost:3000`).

**Safe to re-run**: by default it reuses an existing admin API key rather
than silently rotating it (which would break anything already using the
old one). Pass `--rotate` if you deliberately want a fresh key.

Expect output ending in `Updated function "claude_cli".` (or `Created and
activated...` on first run) and the API key printed at the end — save it,
you'll need it again for step 8's MCP Valve update if you use MCP.

**Doing it by hand instead** (if you'd rather not run a script that logs
into the container), the two steps individually:

1. Admin Settings (gear icon) → **Authentication** → toggle **API Keys**
   on. Settings (your own account) → **Account** → **API Key** section →
   **Create new key**. Copy the `sk-...` value.
2. Then:

   ```bash
   export OPEN_WEBUI_BASE_URL=http://localhost:3000
   export OPEN_WEBUI_API_KEY=sk-...   # from step above
   python3 docs/ichirouganaim-integration/sync_pipe.py docs/ichirouganaim-integration/claude_cli.py
   ```

Either way, confirm the model shows up:

```bash
curl -s $OPEN_WEBUI_BASE_URL/api/models -H "Authorization: Bearer $OPEN_WEBUI_API_KEY" \
  | grep -o '"id": *"claude_cli"'
```

(`sync_pipe.py` re-runs cleanly after edits too — `claude_cli.py` changes
take effect immediately on the next sync, no container restart needed.)

## 7. Authenticate the `claude` CLI inside the container (one-time)

This is the one step that genuinely can't be scripted — it needs a real
browser to complete an OAuth login, and needs to run against a real TTY:

```bash
docker exec -it open-webui claude auth login
```

Prints a URL (open it in any browser, doesn't have to be on the same
machine) and either completes automatically or asks you to paste a code
back into the terminal. Once done, this persists in the data volume
(`CLAUDE_CONFIG_DIR`) — surviving container restarts and image rebuilds,
but **not** surviving the *volume* itself being deleted/recreated, at
which point it needs redoing.

Confirm:

```bash
docker exec open-webui claude auth status
# {"loggedIn": true, "authMethod": "claude.ai", ...}
```

## 8. (Optional) Wire up MCP tool access

Skip this section entirely if you just want plain chat through `claude_cli`
with no tools — steps 1-7 are already a complete, working setup for that.

Setting the `MCP_SERVER_URL` Valve does two things at once: it points the
CLI at your MCP server, *and* activates a locked-down flag combo
(`--strict-mcp-config --tools "" --permission-mode bypassPermissions`) that
removes every other tool and waives approval for the one configured MCP
server. That pairing is only safe together — see `claude_cli.py`'s own
comments and [`decisions.md`](decisions.md) for the full reasoning,
including why this needs the CLI to run as a non-root user
(`claude-runner`, set up automatically by `Dockerfile.claude-cli` /
`claude_cli.py`) rather than as root.

**First, confirm the container can actually reach your MCP server** —
don't just assume it based on it working from the host:

```bash
docker exec open-webui curl -sS -o /dev/null -w "%{http_code}\n" --max-time 5 <your MCP URL>
```

A real HTTP status code (even a 4xx) means it's reachable. A connection
error means the URL is wrong for this container's network — if the MCP
server runs on the same host machine (outside Docker), use
`http://host.docker.internal:<port>/...` (works because of the
`extra_hosts` entry from step 2); if it runs elsewhere, use its real
network address.

Then set the Valve:

```bash
curl -s -X POST $OPEN_WEBUI_BASE_URL/api/v1/functions/id/claude_cli/valves/update \
  -H "Authorization: Bearer $OPEN_WEBUI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"MCP_SERVER_URL":"<your MCP URL>"}'
```

**Or, packaged as a script** (does the same reachability check plus a
readback confirming the write actually took, rather than trusting "the
API call didn't error"):

```bash
docs/ichirouganaim-integration/configure_mcp.sh <your MCP URL>
docs/ichirouganaim-integration/configure_mcp.sh ""   # clears it, disables MCP for claude_cli
```

## 8b. (Optional) Register the MCP server for *every* model, not just `claude_cli`

Step 8 above only wires the MCP server into `claude_cli` specifically —
the `claude` CLI subprocess connects to it directly, bypassing this
fork's own MCP client entirely. If you also want native (non-`claude_cli`)
models in this instance to be able to use the same MCP server, that's a
genuinely different, independent mechanism: this fork's built-in **Tool
Server** support
(`backend/open_webui/routers/configs.py`'s `/api/v1/configs/tool_servers`
endpoints). The two don't conflict — the MCP server ends up with two
separate client connections into it, which any real MCP server is
designed to handle.

```bash
docs/ichirouganaim-integration/register_mcp_tool_server.sh \
  --id ichirouganaim_mcp \
  --url <your MCP URL> \
  --name "Ichirouganaim MCP" \
  [--public]
```

Verifies the MCP server actually responds (via a real handshake, no
Claude usage spent) before saving, and re-running with the same `--id`
updates the existing entry in place rather than duplicating it. Without
`--public`, the registered connection defaults to **admin-only** access
(confirmed by reading `has_connection_access` directly — no
`access_grants` configured means only admins can use it); `--public`
grants read access to every user via the exact grant shape `has_access`'s
own docstring documents for that.

**Registering it makes it *available*, not automatically used by every
model.** A chat still needs `tool_ids` containing
`"server:mcp:<your-id>"` for that specific request to actually connect
and call it. **Confirmed live (frontend source, not assumed): there's
currently no way to make a model auto-use a Tool Server by default at
all** — a model's own edit page (`Workspace → Models → edit` →
`ToolsSelector.svelte`) only lets you pick from the internal Tools
registry (`$lib/apis/tools`, a separate, older mechanism — individually
registered Python function tools, not Tool Server connections), and
doesn't reference `tool_server.connections` at all. The *only* way to
enable a registered Tool Server for a conversation is per-chat: the "+"
tools icon in the message input toolbar, which opens
`ToolServersModal.svelte` listing both internal Tools and Tool Servers —
select it there, every time, for every chat that needs it.

**Where to check it's registered**: Admin Settings (gear icon) →
**Integrations** tab (labeled "External Tool Servers" in the UI,
`Integrations.svelte`) — the connection this script created should be
listed there, editable/removable the same as one added by hand.

## 9. Verify end to end

Plain chat:

```bash
curl -sS -N $OPEN_WEBUI_BASE_URL/api/chat/completions \
  -H "Authorization: Bearer $OPEN_WEBUI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude_cli","messages":[{"role":"user","content":"Reply with just: pong"}],"stream":true}'
```

Should stream back real `chat.completion.chunk` SSE events ending in
`pong` and `[DONE]`. If MCP is configured, also try a message that
actually needs a tool call, and confirm a genuine tool response comes
back (not just that the request doesn't error).

Or just open the web UI, pick `claude_cli` from the model dropdown, and
send a message. With MCP configured, a tool call should render as the
same collapsible "Executing X.../View Result from X" card native
tool-calling produces (not raw JSON dumped into the chat) — confirms the
step 4 work. If the MCP server exposes a `get_record_graph_url`-style tool
and the model calls it, that one specific call should instead render as a
small "View Graph" pill that opens a modal with the URL in an iframe when
clicked — confirms step 5. Both need the frontend to have actually been
rebuilt with this checkout's own source (see step 3's memory note) — the
troubleshooting table below covers what it looks like when that hasn't
happened.

## Ongoing maintenance

- **Disk space**: check `docker system df` periodically; `docker builder
  prune -f` if build cache creeps back up. See the Prerequisites section
  above for why this specifically matters here.
- **Editing the Pipe**: edit `docs/ichirouganaim-integration/claude_cli.py`,
  re-run `sync_pipe.py` — takes effect immediately, no restart needed. This
  is a hot-sync straight into the running instance's DB, unrelated to the
  image build below — the two update mechanisms are genuinely different
  and don't substitute for each other.
- **Rebuilding the image**: needed when `Dockerfile.claude-cli` itself
  changes (e.g. bumping the pinned `claude-code` version) **or when any
  frontend source file changes** (anything under `src/`, e.g. further
  edits to `GraphCard.svelte`/`GraphModal.svelte`/`graph-url.ts`/
  `ToolCallDisplay.svelte`) — as of the step 4/5 work, the image bakes in
  a real build of this checkout's frontend (see step 3), so a frontend
  change with no rebuild is invisible in the running container, unlike a
  `claude_cli.py` edit:
  `docker compose -f docker-compose.yaml -f docker-compose.override.yaml build && ... up -d`.
- **Bumping the pinned `claude-code` version**: edit the version in
  `Dockerfile.claude-cli`'s `npm install -g @anthropic-ai/claude-code@X.Y.Z`
  line, rebuild. Don't remove the pin entirely (see Prerequisites and
  `decisions.md` for why an unpinned version bit this project once).

## Long-term operation (days into weeks into months)

Everything above gets a fresh deployment working. This section is about
what can quietly go wrong (or need attention) the longer it stays up, and
what's actually automatable about that versus what genuinely needs a human
— see `decisions.md`'s 2026-08-22/23 entries for the full reasoning behind
each of these.

**The one thing that matters most, and can't be automated away**: the
`claude` CLI's own OAuth login (step 7) is what everything else depends
on. It should keep working indefinitely via normal token refresh, but
*will* break if the Claude.ai subscription lapses, the session gets
revoked from Claude.ai's own account settings, or Anthropic forces a
re-auth for a security reason. When it breaks, `claude_cli.py` fails
cleanly (a visible error in the chat, not a crash) — but the fix always
needs a human with a real browser (`docker exec -it open-webui claude auth
login`), the same as initial setup. Nothing here can script around that;
the best available mitigation is finding out *before* someone hits a
broken chat:

```bash
docs/ichirouganaim-integration/check_claude_auth.sh
```

Exits 0 if logged in, 1 with a clear message otherwise — safe to run on a
schedule (cron, a monitoring system, whatever's available) purely for
early warning. Never modifies anything.

**Things that are handled automatically now, no action needed**:

- `sessions.json` (the chat-id → claude-session-id map) used to grow
  forever — confirmed by reading the code, it was only ever pruned on a
  hard CLI failure, never for successful chats or deleted ones. Fixed
  directly in `claude_cli.py`: it's now bounded to the 500 most recently
  used chats (same strategy the reference implementation this was ported
  from already used, see that constant's own comment), evicting the
  least-recently-used entry once over that bound. Nothing to run
  periodically for this anymore.

**Things worth checking periodically, informational only — nothing here
changes anything on its own**:

- **A newer `claude-code` version might exist.** The pin is deliberate
  (Prerequisites/`decisions.md` — an unpinned "latest" once silently
  swallowed a real error), so nothing should auto-bump it. This just
  reports what's pinned vs. what's current, with the manual steps to
  adopt a newer one if you decide to:

  ```bash
  docs/ichirouganaim-integration/check_claude_code_version.sh
  ```

- **Docker disk usage** — same `docker system df` / `docker builder prune
  -f` guidance from the Prerequisites section and "Ongoing maintenance"
  above, wrapped as a script for convenience if you want to put it on a
  schedule instead of remembering to run it by hand:

  ```bash
  docs/ichirouganaim-integration/docker_disk_cleanup.sh
  ```

**Back up the data volume.** Chat history, the admin account, the synced
`claude_cli` Pipe function, and — critically — the `claude` CLI's own
OAuth login all live in one Docker volume with no automatic backup.
Nothing destroys it in normal operation, but an accidental `docker compose
down -v`, a Docker Desktop reset, or host disk failure wipes all of it at
once, including that OAuth login — meaning a full re-setup from scratch,
browser-based `claude auth login` included. Worth doing periodically for
any deployment meant to stay up for months:

```bash
docs/ichirouganaim-integration/backup_data_volume.sh [output-dir]
```

Auto-discovers the actual volume name from the running container (it's
not literally called `open-webui` — Compose prefixes it with the project
name, which varies by checkout — confirmed live, don't hardcode it).
Restore instructions are in the script's own header comment; broadly:
extract the tarball into a *fresh, empty* volume, not on top of a live
one.

**A design tradeoff worth knowing about, not something to silently
change**: `Dockerfile.claude-cli` builds `FROM
ghcr.io/open-webui/open-webui:main`, a moving tag, not a fixed version.
Any future rebuild — even one done only to bump the `claude-code` pin —
pulls whatever upstream's `main` looks like *at that moment*, potentially
bundling in unrelated upstream changes along with the intended one. If
predictable rebuilds matter more than staying current with upstream,
consider pinning to a specific upstream version tag instead; this wasn't
changed here since it's a real tradeoff, not an obvious fix.

**Genuine unknowns — not investigated, no automation possible without
knowing more**:

- How long Anthropic retains a resumable CLI session's transcript
  server-side (the `--resume <id>` mechanism `claude_cli.py` relies on for
  chat continuity). A very old, dormant chat might fail to resume after
  enough inactivity and just start a fresh session instead — not
  destructive, but worth knowing the exact window isn't documented
  anywhere this project has access to.
- Whether `ichirouganaim_mcp` (a separate, host-native process — see
  `decisions.md`'s 2026-08-22 "Frontend build stage runs out of memory"
  entry for how the full three-piece stack is laid out) has its own
  credential or session that could expire independently of the `claude`
  CLI's own login. Not reviewed as part of this integration.

**Concurrency: how many users can chat through `claude_cli` at once.**
Multiple users *can* use it simultaneously — `pipe()` spawns an
independent subprocess per request, not one serialized process, and a
real `sessions.json` race condition that could have corrupted concurrent
chats' session continuity was found and fixed (see decisions.md's
2026-08-23 concurrency-testing entry for the full story, including why
the first fix attempt looked correct and wasn't). But there's a real
capacity ceiling to plan around: **each concurrent request spawns a whole
subprocess tree** (`setpriv` → the `claude` binary → its own `node`
runtime → the sandboxing layer), not one lightweight process — confirmed
live, the container's PID count jumped to 150-190 for only 12-25
concurrent requests. On a memory-constrained machine that adds up fast:
on this session's own 3.83GiB-limited dev machine, 12 concurrent requests
ran cleanly but 15 crashed the container outright (confirmed via
`docker inspect`'s `RestartCount` incrementing, not just a slow
response). That ceiling is this machine's own memory budget, not
`claude_cli.py`'s design — the same conclusion this file's memory
Prerequisites bullet already reached for the frontend *build*, now
confirmed to apply to request-serving *load* too.

**This needs re-testing on whatever machine actually runs this in
production** — the numbers above are specific to a 3.83GiB-limited dev
machine, not a general limit. Use the included test tool, starting small
and working up rather than jumping straight to a large number:

```bash
export OPEN_WEBUI_API_KEY=sk-...
docs/ichirouganaim-integration/concurrency_test.sh 5
docs/ichirouganaim-integration/concurrency_test.sh 15
docs/ichirouganaim-integration/concurrency_test.sh 50
```

It fires N genuinely concurrent completions, verifies each gets its own
uncrossed response back, and prints the container's memory/PID trace for
the run — if a run crashes the container, that trace plus
`docker inspect <container> --format 'restartCount={{.RestartCount}}'`
confirms it, the same way it was diagnosed this session. Spends real
Claude usage — one real completion per concurrent request in the test.

**Important caveat: the numbers above are for plain chat only, not real
MCP/deed-entry-style workflows, and probably don't transfer** —
`concurrency_test.sh` sends a single-turn "echo this token back" prompt,
finishing all N requests in 16-21s even at N=25, which likely means not
every request was ever *fully* concurrent with every other one. A real
deed-entry conversation (`list_workflows` → `get_workflow` → creating
records/events/parties → finalize) runs many tool-calling rounds over
minutes, not seconds — making genuine full overlap across N concurrent
users *more* likely, not less, which points toward a *lower* safe N than
what's measured here, not the same one. It also hits three more services
this integration hasn't reviewed the concurrency limits of at all:
`ichirouganaim_mcp`, `ichirouganaim`-django, and its MySQL database — any
one of those could become the real bottleneck before `open-webui`'s own
container memory does. **A real deed-entry-style concurrency test, run
against that whole stack together, is still an open item** — deliberately
not run on the dev machine this session (it already crashes under plain
chat at N=15; a heavier MCP-tool-calling version would almost certainly
crash it faster while spending substantially more real Claude usage per
attempt, for data that wouldn't answer where the real ceiling is or which
service hits it first). See `decisions.md`'s 2026-08-23 entry for the full
reasoning. Don't treat the N=12/15 numbers above as a deed-entry capacity
plan — they're a plain-chat baseline only.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Exec format error` running `claude` inside the container | Wrong CPU architecture got installed. Shouldn't happen given the automatic `TARGETARCH` resolution, but if it does, this is the first thing to check — confirm `docker exec open-webui uname -m` matches what `Dockerfile.claude-cli` targeted. |
| `--dangerously-skip-permissions cannot be used with root/sudo` | The CLI ran as root instead of `claude-runner`. Check `docker exec open-webui id` reports the expected setup exists, and that `claude_cli.py`'s `_prepare_privilege_drop()` logic hasn't been broken by an edit. |
| Chat with `claude_cli` returns nothing at all, no error, but the request completes (exit 0) | Almost certainly disk space, even though it doesn't look related — see Prerequisites. Check `docker exec open-webui df -h /` and `docker system df`. |
| `claude auth status` unexpectedly shows `loggedIn: false` after previously working | The data volume was recreated (not just the container) — re-run `claude auth login` (step 7). |
| MCP tool calls fail or time out | Re-check reachability *from inside the container* (step 8's `curl` check), not just from the host — these are genuinely different network paths. |
| `docker compose build` fails during `npm run build` with `JavaScript heap out of memory` or `SIGKILL`/`cannot allocate memory` | Docker doesn't have enough memory allocated for the frontend build stage — see the Prerequisites section's memory bullet and `decisions.md`'s 2026-08-22 "Frontend build stage runs out of memory" entry. Give Docker more memory (Docker Desktop: Settings → Resources → Memory) and retry; stopping other running containers to free memory does *not* help (confirmed live) — it's the VM's total allocation ceiling, not contention. |
| A tool call that should show the "View Graph" card instead renders as a generic "View Result from `mcp__ichirouganaim_mcp__get_record_graph_url`" row | Either the frontend build in step 3 didn't actually pick up `GraphCard.svelte`/`GraphModal.svelte`/`graph-url.ts` (confirm the image was rebuilt *after* these files existed in the checkout, not before), or the tool result didn't parse as a URL (`extractGraphUrl` falls through to the generic renderer rather than showing nothing — see `src/lib/utils/graph-url.ts`'s docstring for the shapes it handles). |
| The container becomes unreachable / restarts under concurrent chat load | Almost certainly memory exhaustion, not a code bug — see the "Concurrency" section above and `decisions.md`'s 2026-08-23 entry. Confirm with `docker inspect <container> --format 'restartCount={{.RestartCount}}'` (incrementing means it genuinely crashed) and re-run `concurrency_test.sh` at a lower N to find where it stops happening on this specific machine. |
