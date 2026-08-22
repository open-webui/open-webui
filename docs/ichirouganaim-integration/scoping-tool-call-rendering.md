# Scoping: tool-call `output`-item rendering + graph-url card (build order steps 4-5)

**Status: built and live-verified, one step left.** Steps 4 (tool-call
`output`-item emission, `claude_cli.py`) and 5 (`graph-url.ts`/
`GraphCard.svelte`/`GraphModal.svelte`/the `ToolCallDisplay.svelte` branch)
are both implemented and confirmed working — step 4 through the real
running `:3000` Docker container, step 5 through a real screenshot of a
local dev-mode frontend build talking to that same container (see
`decisions.md`'s 2026-08-22 entries for both). **What's left**: the real
`:3000` container still serves the *stock* upstream frontend bundle, not
one built from this checkout's own source — `Dockerfile.claude-cli` now has
a frontend-build stage that fixes this, but building it locally hit a real
memory ceiling (Docker Desktop's VM only had 3.8GB, not enough for the
Vite/Rollup production build — confirmed via two different failure modes,
see decisions.md). Decision: move the build to a separate, more capable
machine (a Mac Studio) rather than raise memory on this one — `SETUP.md`
has been updated with everything a fresh build on that machine needs,
including the memory requirement this session discovered the hard way. This
file is otherwise still useful for a fresh session picking this back up —
read it first, then the "Read first" list below, in order.

## Where this picks up

Part 1 of [`scoping-claude-cli-and-graph-modal.md`](scoping-claude-cli-and-graph-modal.md)
(the `claude-cli` Pipe itself) is **done and live-verified**, including
build order steps 1-3, MCP wiring, the non-root sandbox
(`Dockerfile.claude-cli`), and a full real multi-turn deed-entry workflow
session through the actual running Docker deployment (`list_workflows` →
`get_workflow` → volume/record/event creation → graph review → ready to
finalize — real MCP tool calls against `ichirouganaim_mcp`, not a mock).
`SETUP.md` documents how to stand up and reach that running instance.

**What's still open** — the original doc's build order steps 4 and 5:

> 4. Tool-call `output`-item emission, matching native tool-calling's
>    visual output.
> 5. Graph-url extraction module + `GraphCard`/`GraphModal`, verified
>    against a real captured `get_record_graph_url` result...

**Confirmed live, this session**, why step 5 depends on step 4 and isn't
independent: tested the deed-entry workflow through the browser UI right
now. Every MCP tool call the model made (`list_workflows`, `get_workflow`,
record/event creation, the graph URL response) rendered as the model's own
prose narration ("Now recording the object and the three people... Now
attaching the parties...") with the graph URL appearing as a plain
Markdown-autolinked URL in that text — **not** as a tool-call card at all,
because `claude_cli.py`'s `pipe()` only ever `yield`s bare text strings
right now (see its own code — no `__event_emitter__` calls). Step 5's
`GraphCard`/`GraphModal` plan assumes tool calls already render as the
normal collapsible card and just special-cases one of them; without step 4
there's no card to special-case. Build step 4 first.

## Read first

- [`scoping-claude-cli-and-graph-modal.md`](scoping-claude-cli-and-graph-modal.md)
  — the original scoping doc. Its "Tool-call rendering — the part that
  isn't free" subsection (under Part 1) and all of "Part 2: the graph-url
  card + modal" are the design for steps 4-5 — this file doesn't repeat
  that content, only adds what's changed or been confirmed since.
  **Re-verify its file:line citations before trusting them** — they were
  written during initial scoping, some time and unrelated repo activity
  has passed since. Spot-checked two just now and both still exist at the
  cited paths (`src/lib/components/chat/Messages/structuredOutput.ts`,
  `src/lib/components/common/ToolCallDisplay.svelte`) — the rest weren't
  re-checked.
- [`decisions.md`](decisions.md) — full history of Part 1, including two
  real bugs fixed after this doc might otherwise seem "done": an
  `ENOSPC`-swallowing bug in an old pinned `claude-code` version (fixed by
  pinning `2.1.239`), and an `asyncio.LimitOverrunError` from
  `create_subprocess_exec`'s default 64KB line-buffer limit blowing up on
  large MCP tool results (fixed by an explicit `limit=32MB`). Both matter
  here: any change to how `claude_cli.py` reads/handles subprocess output
  for step 4 needs to preserve both fixes, not reintroduce either bug.
- `docs/ichirouganaim-integration/claude_cli.py` — the actual Pipe source
  step 4 modifies. Current `pipe()` only handles `stream_event`'s
  `content_block_delta`/`text_delta` (plain text). It does **not** yet
  read the `assistant` message type's `tool_use` blocks or the `user`
  message type's `tool_result` blocks at all — those are the two cases to
  add, mirroring `ClaudeCliTranslator.handleAssistant`/`handleUser` in the
  reference repo's `claude-cli-provider.ts` (Part 1's own read-first list).
- [`SETUP.md`](SETUP.md) — how to stand up / reach the real running
  instance to test against. `bash docs/ichirouganaim-integration/bootstrap.sh`
  gets you an API key + synced Pipe in one step if starting from a fresh
  container.

## What's genuinely new here vs. the original doc

**Tool naming will differ from what Part 2 originally assumed**, because
step 4 is being built *inside the claude-cli Pipe*, not as open-webui's
native MCP tool-calling. Part 2's "Tool name matching" section warns about
*this fork's own* MCP client namespacing (`{server_id}_{tool_name}`,
`middleware.py:2765-2772` at time of original scoping) — that's the code
path for native (non-claude-cli) models using Tool Servers, which is **not**
what runs here. For claude-cli, the `claude` binary itself assigns tool
names, following its own `mcp__<server-key>__<tool>` convention (confirmed
in the original doc's Part 1 mapping table, sourced from the reference
repo). Since `claude_cli.py`'s `_build_args()` names the configured server
`"mcp"` (`{'mcpServers': {'mcp': {...}}}`), expect tool names shaped like
`mcp__mcp__get_record_graph_url` — **verify this live** (a real captured
`assistant` message's `tool_use.name` from a fresh test run) rather than
trusting this paraphrase; the exact string matters for `isGraphUrlTool()`'s
match logic in step 5.

**No raw tool-call JSON was captured from this session's browser test** —
what's quoted in this repo's chat history (with the user) is the
*rendered* prose the model produced, not the underlying `assistant`/`user`
JSONL messages `claude` actually emitted. Before writing step 4's
translation logic, capture that raw shape for real: run a similar
MCP-tool-calling prompt directly (`curl` against `/api/chat/completions`
with `MCP_SERVER_URL` set, same as verification patterns already in
`SETUP.md`/`decisions.md`), and either add temporary logging inside
`claude_cli.py`'s `pipe()` loop or capture the subprocess's raw stdout
directly, to see actual `assistant.message.content[].tool_use` and
`user.message.content[].tool_result` blocks — same "read the real stored
value, not a reconstructed approximation" discipline the original doc's
`graph-url.ts` reference and this project's `decisions.md` both lean on
throughout. This is the natural first live-verification step for step 4,
not a footnote.

## Suggested order

1. Capture a real `assistant`/`tool_use` and `user`/`tool_result` JSONL
   pair live (see above) — confirms the exact tool-name format and result
   shape before writing translation code against assumptions.
2. Implement step 4 in `claude_cli.py`: handle the `assistant` and `user`
   message types (currently unhandled — `pipe()`'s `if/elif` chain only
   has `stream_event` and `result`), emit `__event_emitter__` calls shaped
   to match `structuredOutput.ts`'s `function_call`/`function_call_output`
   items, and persist the same `output` array via
   `Chats.upsert_message_to_chat_by_id_and_message_id` (both approaches
   specified in the original doc's Part 1).
3. Verify structurally first (does a tool call render as the normal
   "Executing X.../Tool Executed" card at all, matching a native
   tool-calling model's look) before layering step 5 on top.
4. Build step 5 per the original doc's Part 2 plan (`graph-url.ts`,
   `GraphCard.svelte`, `GraphModal.svelte`, the `ToolCallDisplay.svelte`
   branch) — re-verify its file:line citations and the MCP result-shape
   extraction live, per its own "re-verify, don't assume" section, using
   the real graph URL this session already saw as a starting example, not
   a substitute for a fresh live capture.
5. Live-verify the whole thing by re-running a real deed-entry-style
   prompt through the browser UI (or `curl`) and confirming an actual
   clickable graph card + modal appears — the same kind of end-to-end
   check that caught the `ENOSPC` and `LimitOverrunError` bugs earlier
   rather than trusting structural correctness alone.

## Standing agreements that still apply

- **Ask before spending subscription usage** on a live `claude` CLI
  invocation for verification — same working agreement as Part 1.
- **Consistency requirement** (from the original doc): reuse
  `Modal.svelte`, match `CitationsModal.svelte`'s card conventions, no new
  icon/color/modal chrome. Verify by running the dev server and comparing
  against an existing tool-call/model side by side, not just by reading
  the Svelte source.
- Keep logging real decisions and fixes in `decisions.md` as this gets
  built, same discipline as Part 1 — cite real file:line locations, call
  out live-verified vs. assumed explicitly.
