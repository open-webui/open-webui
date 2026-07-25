# Frontend: splitting and reusing components

Target shape for `src/`. Applies to **new components and to components you are already
substantially changing**. It is not a mandate to go rewrite working screens.

## Why

The largest components are page-sized god objects:

| File                                                          | Lines |
| ------------------------------------------------------------- | ----: |
| `lib/components/chat/Chat.svelte`                             |  3291 |
| `lib/components/chat/MessageInput.svelte`                     |  2157 |
| `lib/components/workspace/Knowledge/KnowledgeBase.svelte`     |  1808 |
| `lib/components/chat/Settings/Advanced/AdvancedParams.svelte` |  1698 |
| `lib/components/layout/Sidebar.svelte`                        |  1659 |
| `lib/utils/index.ts`                                          |  2145 |
| `lib/apis/index.ts`                                           |  1647 |

`KnowledgeBase.svelte` is the one we own and the one to reason from: **1240 of its 1808
lines are `<script>`** — 42 top-level `let` declarations and ~36 handler functions
covering KB metadata editing, drag-and-drop, three separate upload paths (modern
browser / Firefox / directory sync), folder CRUD, file CRUD, move operations, a
debounced content editor, and a media query listener.

What that costs:

- **Nothing in it is testable.** The only frontend unit test in the repo is
  `lib/utils/knowledge.test.ts`, and it only exists because `withStatsOutdated` was
  _pulled out_ of this component.
- **Reuse is impossible.** The upload/dedup logic is needed by chat attachments and by
  notes, but it's welded to this component's 42 state vars.
- **Every change risks the whole screen.** 36 handlers over shared mutable state means
  no local reasoning.

## The precedent to copy

`KnowledgeBase/` already shows the right shape — the parent kept the state, the children
became presentational:

```
workspace/Knowledge/
  KnowledgeBase.svelte                 1808  ← container (still too big)
  KnowledgeBase/
    Files.svelte                        293  ← presentational
    DirectoryRow.svelte                 212
    AddTextContentModal.svelte          166
    AddContentMenu.svelte               145
    KnowledgeBreadcrumbs.svelte          89
    NewDirectoryModal.svelte             79
```

Those children own no business logic: they take data in as props and report intent back
through callback props. `Files.svelte`:

```svelte
export let files = [];
export let directories = [];
export let selectedFileId = null;

export let onClick = (fileId) => {};
export let onDelete = (fileId) => {};
export let onRename = (fileId: string, name: string) => {};
export let onNavigateDirectory = (directoryId: string) => {};
export let onMoveFileToDirectory = (fileId: string, directoryId: string) => {};
```

**Aim for children in the 50–300 line range and containers under ~400.**

## Four kinds of module

| Kind               | Home                                     | Owns                                       |
| ------------------ | ---------------------------------------- | ------------------------------------------ |
| **Page**           | `src/routes/**/+page.svelte`             | routing, params, page-level data load      |
| **Container**      | `lib/components/<domain>/X.svelte`       | state, API calls, orchestration            |
| **Presentational** | `lib/components/<domain>/X/Child.svelte` | markup + local UI state only               |
| **Logic**          | `lib/utils/<domain>.ts`                  | pure functions — **this is what you test** |

Anything genuinely generic goes in `lib/components/common/` — check there first, it
already has `Modal`, `ConfirmDialog`, `InputModal`, `Tooltip`, `Dropdown`, `Pagination`,
`Badge`, `Spinner`, `Switch`, `Select`, `Checkbox`, `FileItem`, `Folder`, `Collapsible`,
`Textarea`, `SensitiveInput`, `PDFViewer` and more. Re-implementing one of these is the
most common avoidable duplication in this codebase.

## Conventions (already established — follow them)

**Callback props, not `createEventDispatcher`.** 83 components still use the dispatcher
(upstream code, `on:confirm` / `on:cancel`); every component our fork added uses typed
`on<Verb>` props with a no-op default. Use callback props in new code. Don't convert
upstream components you aren't otherwise touching.

**Svelte 4 API on the Svelte 5 runtime.** 491 components use `export let`; exactly two
use runes. **Do not migrate to runes piecemeal** — match the file you're in. A rune
migration is a separate, deliberate project.

**`bind:show` for modals**, matching `Modal.svelte` and every existing modal.

**i18n via context**: `const i18n = getContext('i18n')`, then `$i18n.t('...')`. New
strings need `npm run i18n:parse`.

**API wrappers stay in `lib/apis/<domain>/index.ts`** — one dir per backend router. They
are thin `fetch` wrappers that collect the error into a local `error` var and `throw error`
at the end; callers expect a thrown detail string. Never call `fetch` from a component.

## How to split a fat component

Work in this order — it front-loads the value and keeps each step reviewable.

**1. Pure logic → `lib/utils/<domain>.ts`, with a vitest test.**
Anything that maps, formats, filters, derives, or compares. From
`KnowledgeBase.svelte`: `dirPathOf`, `hasHiddenFolder`, `decodeString`, the sync-diff
computation in `collectDirectoryFiles`. This is the highest-value step because it's the
only step that produces tests. Precedent: commit `a23684c2b` extracted
`withStatsOutdated` this way.

**2. Async workflows → a module or store, not the component.**
The three upload paths (`handleModernBrowserUpload`, `handleFirefoxUpload`,
`syncDirectoryHandler`, `collectDirectoryFiles`, `ensureFolderTree` — ~350 lines) are one
cohesive feature: "upload a folder tree into a KB". That belongs in something like
`lib/utils/knowledge-upload.ts` (or a small store if it needs progress state), taking the
API functions and a progress callback as arguments. Then the component just calls it.

**3. Independent markup regions → presentational children.**
A region is ready to extract when it reads a bounded slice of state and reports intent
through a handful of callbacks. Pass data down; never let a child call an API.

**4. Only then consider splitting the container itself.**
If two regions share nothing but the page shell, they're two containers under one page.

**What not to extract:** a child that needs 15 props and 8 callbacks is a bad seam — the
state is genuinely shared, so leave it and split elsewhere. Extraction that just moves
coupling into a prop list makes things worse.

## Opportunistic refactoring

- **New feature** → new presentational component + pure helpers from the start.
- **Editing a fat component** → extract the region or logic you are touching, ship it
  with a test if it's pure. Leave the other 1500 lines alone.
- **Duplicating something** → stop and check `lib/components/common/` and
  `lib/utils/index.ts` first.
- **Never** reformat or restructure an upstream component you weren't otherwise changing.
  It buries the real diff and makes future upstream merges painful.

## Testing

Full policy: **[testing.md](testing.md)**. Every change ships with tests.

`npm run test:frontend` → vitest, default config (no `test` block in `vite.config.ts`),
`*.test.ts` colocated next to the module. `--passWithNoTests` is set, so an empty run
passes — that's a gap, not permission.

Test **pure logic** (`lib/utils/*.ts`). Don't try to mount and test the fat containers;
extract the logic worth asserting and test that instead. `lib/utils/knowledge.test.ts`
is the model: small, colocated, asserts behaviour including the reference-identity
contract that Svelte reactivity depends on.

**This is what makes step 1 of the splitting order non-optional.** There is no browser
E2E harness in this repo (Cypress is vestigial — no config, no specs; the Playwright
compose file is the web _loader_ engine, not a test runner). So a UI feature is only
coverable two ways: pull its decision-making into `lib/utils/<domain>.ts` and unit-test
it, and cover the endpoint it calls with a backend integration test. Logic left inline in
a 1800-line component is, in practice, untestable — which is the whole argument for
splitting.

`npm run check` (svelte-check) is the type gate. Adding types to props while extracting
a component is cheap and worth it — many existing props are untyped (`export let
knowledge = null`).
