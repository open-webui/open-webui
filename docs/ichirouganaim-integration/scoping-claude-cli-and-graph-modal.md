# Scoping: claude-cli model + graph-url card/modal for this open-webui fork

**Status: scoped, not built.** Written so a fresh chat/session can go
straight into implementation without re-deriving context — read this file
first, then the "Read first" list below, then start on Part 1.

## Why this exists

A parallel project, `ichirouganaim_frontend` (sibling repo, Next.js), was
built from scratch as a chat UI for the same backend this fork will talk
to — an MCP server (`ichirouganaim_mcp`) fronting a Django API
(`ichirouganaim`) for transcribing historical records ("deeds"). That
frontend already solved everything this fork needs, including things this
fork already has for free (multi-user auth, DB-backed chat history, a
model/provider system) — proof-of-concept work, not wasted, but this fork
turns out to need far less new code for the same result: two gaps, not a
whole application.

**The two gaps**, confirmed by reading `ichirouganaim_frontend`'s working
implementation and investigating this fork's actual extension points
(not assumed — see "Read first"):

1. This fork has no way to chat through a Claude.ai subscription via the
   local `claude` CLI (`ichirouganaim_frontend` calls this the
   `claude-cli` provider) — every other model here is a real API/local
   backend.
2. This fork renders every tool call's result the same generic way — no
   special treatment for `get_record_graph_url`, whose result should
   render as a small clickable card that opens a modal with the returned
   URL in an iframe, not a JSON dump.

Both are additive, isolated changes — confirmed during scoping that
neither needs a core fork or new backend architecture. See Parts 1 and 2
below for exactly where each hooks in.

## Read first

- `/Users/IanBarrow/code/FULL-ICHI/ichirouganaim_frontend/lib/claude-cli-provider.ts`
  — the reference behavior for Part 1. Exact CLI invocation (flags,
  `--mcp-config` shape), the `stream_event`/`assistant`/`user`/`result`
  JSONL translation logic, and the `sessionIdByChatId` `--resume`
  mechanism. Port the *behavior*, not the TypeScript — Part 1 below maps
  each piece to its Python/open-webui equivalent.
- `/Users/IanBarrow/code/FULL-ICHI/ichirouganaim_frontend/components/GraphCard.tsx`,
  `GraphModal.tsx`, and `lib/graph-url.ts` — the reference behavior for
  Part 2. Read `graph-url.ts`'s docstring in full: it documents three
  real, live-verified output shapes and a chain of bugs found only by
  checking actual captured data, not assumption. That discipline carries
  over here — see "Working style," below.
- `docs/scoping-phase-8-robustness-and-polish.md` in
  `ichirouganaim_frontend` (and its promoted content in that repo's
  `decisions.md`, Phase 8 entry) — not directly relevant technically, but
  the template this file itself follows, and an example of what a
  finished phase-log entry looks like once this work is done.

## Consistency requirement — read before writing any UI code

Everything built here needs to **look and feel like it already belongs**
in this fork, not like a bolted-on feature:

- Reuse existing components exactly as they are: `Modal.svelte` for the
  graph modal (don't hand-roll backdrop/escape-key handling —
  `GraphModal.tsx`'s reference version did that only because no `Modal`
  primitive existed in that codebase; this one already has it), the same
  card/spacing/typography conventions already used for e.g.
  `CitationsModal.svelte`.
- The claude-cli Pipe's tool-call rendering should produce the **same
  visual "Executing X.../Tool Executed" collapsible card** that native
  tool-calling produces — not a bespoke look. That means matching the
  Responses-API-shaped `output` items real tool-calling emits (see Part
  1), not inventing a different event shape that happens to render
  differently.
- No new icon style, no new color palette, no new modal chrome. If a
  visual decision isn't obvious from an existing analog, find the closest
  existing pattern in this fork and match it rather than designing fresh.
- Verify this by actually running the dev server and looking at it next
  to an existing model/tool-call in the UI — not just by reading the
  Svelte code and assuming it matches.

## Part 1: `claude-cli` as a Pipe function

### The extension point (confirmed, not assumed)

Open-webui's "Functions" plugin system, specifically a **Pipe** function.
Storage is a DB row (`Function.content` = raw Python source,
`backend/open_webui/models/functions.py:19-34`), loaded via `exec()` into
a synthetic module by `load_function_module_by_id()`
(`backend/open_webui/utils/plugin.py:259-304`), which looks for a
`class Pipe:`. No core file needs to change — `get_function_models()`
(`backend/open_webui/functions.py:71-147`) automatically adds every
active Pipe function to the model dropdown, merged in
`backend/open_webui/utils/models.py:56-64` alongside the real backends.

**Keeping the source in version control**: `load_function_module_by_id`
takes `content` as a parameter when provided (used by the `/load/url`
admin endpoint and direct API calls) and only falls back to reading the
DB row when `content is None`
(`backend/open_webui/utils/plugin.py:264-274`) — there's no
filesystem-directory-scan-at-startup mechanism in this version. So: keep
the actual Pipe source as a real `.py` file in this fork's own repo (not
only pasted into the admin UI), and sync it into the running instance's
DB via the API (`POST /api/v1/functions/create` the first time,
`POST /api/v1/functions/id/{id}/update` after — both take `content`
directly, `backend/open_webui/routers/functions.py`). Write a small sync
script early (`docs/ichirouganaim-integration/sync_pipe.py` or similar) so
"edit the file, run the script" is the actual dev loop, not "edit in the
browser and lose the diff." This is the first thing to build, before the
Pipe's actual logic — it's what makes the rest of this reviewable and
documentable.

### Confirmed `Pipe` interface

```python
class Pipe:
    class Valves(BaseModel):
        MODEL: str = ""          # optional --model override, like CLAUDE_CLI_MODEL
        MCP_SERVER_URL: str = "" # like MCP_SERVER_URL in ichirouganaim_frontend's .env
        CLAUDE_CLI_PATH: str = "claude"  # like CLAUDE_CLI_PATH

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,                    # OpenAI-chat-shaped: body["messages"], body["stream"]
        __chat_id__: str,               # -> the sessionIdByChatId key (see below)
        __event_emitter__=None,         # -> tool-call card events (see below)
        __user__=None,
        # add other params only as needed -- the framework passes only
        # what's in this signature (backend/open_webui/functions.py:192-210)
    ):
        ...
```

Declare `Valves` fields for everything `ichirouganaim_frontend`'s
`lib/config.ts` currently reads from env vars for this provider
(`MCP_SERVER_URL`, `CLAUDE_CLI_PATH`, `CLAUDE_CLI_MODEL`) — Valves are
admin-configurable through the UI automatically, no separate settings
page needed.

### Mapping the reference implementation's pieces

| Reference (`claude-cli-provider.ts`) | This fork |
|---|---|
| `spawn(claudeCliPath, args, ...)` | `subprocess.Popen([...], stdout=PIPE, ...)` or `asyncio.create_subprocess_exec` — prefer the asyncio version so `pipe()` can be a real async generator |
| `buildArgs()` — flags | Same flags, ported directly: `-p <message> --output-format stream-json --include-partial-messages --verbose --mcp-config <json> --strict-mcp-config --tools "" --permission-mode bypassPermissions [--model X] [--resume <id>]`. The `--permission-mode bypassPermissions` posture is only safe *because* `--tools ""` + `--strict-mcp-config` already remove every other tool — keep that pairing intact, don't drop one without the other. |
| `sessionIdByChatId: Map<string, string>` | Key off `__chat_id__` the same way. Recommend NOT an in-process dict this time — that's the reference implementation's own documented limitation ("lost on a server restart"). A tiny SQLite table or even a JSON file next to the sync script is enough; this fork's backend already has a real DB (`backend/open_webui/internal/db.py` and friends) if you want to go further and add a proper migration for it. |
| `ClaudeCliTranslator.handle()` line-by-line switch on `stream_event`/`assistant`/`user`/`result` | Same switch, same four cases, in Python. `stream_event` -> yield text/reasoning deltas (see below). `assistant`'s `tool_use` blocks and `user`'s `tool_result` blocks -> tool-call events (see below), not plain text. `result` -> stream end / error. |
| Returns a `UIMessageChunk` stream via `createUIMessageStreamResponse` | `pipe()` as an `async def` generator. Plain `content_block_delta`/`text_delta` text -> `yield delta.text` (a bare string) — `functions.py`'s own chunk-wrapping (`openai_chat_chunk_message_template`, `misc.py:675-704`) turns that into the right SSE shape for free. |

### Tool-call rendering — the part that isn't free

Plain text streaming is "yield a string." Getting the same
"Executing.../Tool Executed" UI that native tool-calling produces is not
automatic — it means constructing the same Responses-API-shaped `output`
items real tool-calling emits and pushing them the same way:
`__event_emitter__({'type': 'chat:completion', 'data': {'output': [...]}})`,
matching the item shapes `src/lib/components/chat/Messages/structuredOutput.ts`
parses (`function_call`/`function_call_output` item types — read that
file for the exact field names before writing this). For persistence
(so the tool call is still there on reload, not just live-streamed),
also write the same `output` array onto the chat message via
`open_webui.models.chats.Chats.upsert_message_to_chat_by_id_and_message_id`
— importable directly, Pipes run as trusted in-process code with full DB
access.

This is genuinely comparable in scope to what `ClaudeCliTranslator`
already does for the AI SDK's `UIMessageChunk` shape in the reference
repo — budget real time for it, don't treat it as a footnote.

### Verification

- Structural stuff (model shows up in the dropdown, Valves save/load,
  plain streaming text renders) can be checked without spending live
  Claude usage — stub `pipe()` to yield canned fake text first, get the
  plumbing right, then swap in the real subprocess call.
- Actually running the `claude` CLI and confirming tool-call cards render
  correctly needs a live invocation. **Ask before spending subscription
  usage** — this project's standing working agreement (carried over from
  `ichirouganaim_frontend`'s sessions) applies here too.

## Part 2: the graph-url card + modal

### Where tool results render today (confirmed, not assumed)

One generic path, no per-tool-name branching anywhere in it yet:
`src/lib/components/common/ToolCallDisplay.svelte` renders every tool
call's result as a collapsible "Executing X.../View Result from X" row
with a raw JSON dump, called from
`src/lib/components/chat/Messages/StructuredOutputRenderer.svelte:78,126`
and `src/lib/components/chat/Messages/Markdown/MarkdownTokens.svelte:397,451`,
both gated only on `detailToken.attributes?.type === 'tool_calls'`. This
fork already has precedent for hardcoded tool-name special-casing on the
*backend* (`backend/open_webui/utils/middleware.py:1100,1130` check
`tool_function_name` for `display_file`/`run_command`) — adding one more
name check in the frontend renderer is idiomatic here, not a new pattern.

### Tool name matching — a real gotcha, ported from the reference repo

This fork's own MCP client namespaces tool names as
`{server_id}_{tool_name}` (single underscore —
`backend/open_webui/utils/middleware.py:2765-2772`), which is *more*
collision-prone than `claude-cli`'s own `mcp__mcp__`-double-underscore
namespacing that `lib/graph-url.ts`'s `isGraphUrlTool()` already had to
work around. Don't do a naive `endsWith('_get_record_graph_url')` --
validate against the actual configured server id for `ichirouganaim_mcp`
(known once it's registered as a Tool Server, or once the claude-cli
Pipe's own `--mcp-config` server key is fixed) rather than pattern-
matching blind.

### Result-shape extraction — re-verify, don't assume

`extractGraphUrl()` in the reference repo is defensive for a reason: it
took three real, live-verified bugs to get right, and each of the three
different providers there produced a genuinely different shape. This
fork's own MCP result-unwrapping
(`process_tool_result()` in `backend/open_webui/utils/middleware.py:869-1082`,
specifically the `elif location:`/MCP branch around lines 990-1053) is a
different code path than either of the reference repo's two providers —
**the shape has to be captured live from this fork's actual running
instance**, not assumed to match. Print/log the raw `attributes.result`
your `ToolCallDisplay.svelte` branch receives for a real
`get_record_graph_url` call before writing the extraction logic, the same
"read the real stored value, not a reconstructed approximation" discipline
`graph-url.ts`'s docstring describes.

### The "embeds" pipeline exists — don't use it

`process_tool_result()` can already push a tool's URL/HTML result into an
always-open inline iframe (`tool_result_embeds`, same file, lines
972-979, rendered via `FullHeightIframe.svelte`). Two reasons it's the
wrong fit here: (1) it's gated to `tool_type in ('external', 'action',
'terminal')` and never fires for a genuine `mcp`-typed call's result, and
(2) its UX is "always rendered inline," which is the opposite of the
reference implementation's deliberate choice — `GraphCard.tsx`'s own
comment explains why: a compact summary card, not a re-rendered full page,
since the graph view is about to be opened full-size on click anyway.
Build the click-to-open card+modal directly in the frontend instead of
extending embeds.

### Concrete plan

1. Small new module (e.g. `src/lib/utils/graph-url.ts`, mirroring the
   reference file's name) with `isGraphUrlTool(toolName, mcpServerId)`
   and `extractGraphUrl(result)` — ported logic, re-verified shape (see
   above).
2. `GraphCard.svelte` — small clickable card, same visual language as
   existing cards in this fork (check `CitationsModal.svelte`'s
   surrounding card markup for the closest existing analog to match).
3. `GraphModal.svelte` — `<Modal size="lg" bind:show>` wrapping an
   `<iframe src={url}>`, mirroring `GraphModal.tsx`'s behavior (URL shown
   in a header, close button, nothing else) using this fork's own
   `Modal.svelte`/close-button conventions instead of hand-rolling either.
4. Wire the branch into `ToolCallDisplay.svelte`: when `isGraphUrlTool`
   matches and the call is complete, render `GraphCard` instead of the
   generic Output block.

## Non-goals

- Multi-user auth, chat history persistence, deed-approval provenance —
  this fork already has real accounts and DB-backed history; none of
  `ichirouganaim_frontend`'s Thrust A work (session cookies, SQLite chat
  store, Django token exchange) needs porting here at all.
- Native (non-`claude-cli`) models talking to `ichirouganaim_mcp` via this
  fork's built-in MCP Tool Server support — confirmed possible
  (`backend/open_webui/routers/configs.py:217-293`), genuinely useful
  later, but a separate, optional piece of work, not part of this scope.
- Anything in `backend/open_webui/utils/middleware.py`'s native
  tool-calling loop itself, or any other core routing file, beyond the
  one small tool-name check in Part 2's frontend renderer.
- Redesigning any existing component's visual language "while you're in
  there" — see "Consistency requirement" above.

## Working style — keep documenting as you go

Mirror `ichirouganaim_frontend`'s own `decisions.md` discipline: as this
gets built, keep a running log in
`docs/ichirouganaim-integration/decisions.md` (create it when the first
real decision gets made, doesn't need to pre-exist empty) — one entry per
real decision or fix, explaining *why*, not just what changed, citing real
file:line locations, and explicitly calling out anything verified against
live/real data vs. assumed. The reference repo's own Phase 7 tail end
(three real bugs in `get_record_graph_url` rendering, only found by
reading actual captured `localStorage` data) is the concrete example of
why this discipline matters here specifically — the same class of bug is
exactly what Part 2's "re-verify, don't assume" section above is trying
to head off in advance.

**Ask before spending subscription usage** (a real `claude` CLI
invocation) — standing working agreement, applies in this fork too.

## Suggested build order

1. The Pipe-source sync script (small, unblocks everything else being
   reviewable/documented as real git diffs instead of admin-UI pastes).
2. Pipe function with stubbed/canned streaming text first — get the
   model-dropdown registration, Valves, and plain SSE streaming verified
   structurally before touching the real subprocess.
3. Real `claude` subprocess + JSONL translation, text streaming only
   (no tool-call cards yet) — first point that needs a live invocation
   and your go-ahead to spend usage.
4. Tool-call `output`-item emission, matching native tool-calling's
   visual output.
5. Graph-url extraction module + `GraphCard`/`GraphModal`, verified
   against a real captured `get_record_graph_url` result from step 3-4's
   live testing (natural point to capture it — no need for a separate
   live session just for this).
