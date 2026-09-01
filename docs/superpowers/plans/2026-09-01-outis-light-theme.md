# Outis-Light Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable `outis-light` theme — the Outis identity (monospace, flat, one green accent) on a light ground — without touching component markup.

**Architecture:** Extract the hue-free half of `outis-mneme-theme.css` into a shared stylesheet keyed on `html:is(.outis-mneme, .outis-light)`, leave each theme file holding only its palette, and register `outis-light` at the three theme-switch sites plus the four CodeMirror hosts.

**Tech Stack:** Tailwind CSS v4 custom properties, SvelteKit, CodeMirror 6, highlight.js.

**Status:** executed on branch `theme/outis-light`. Three things the plan did not anticipate
were found by driving the built app in a browser and are written up in the spec under
"Found during implementation".

**Spec:** `OUTIS_LIGHT_THEME_SPEC.md` (and `OUTIS_MNEME_THEME_SPEC.md` for the mechanism it reuses)

## Global Constraints

- Theme id is `outis-light`; the class list applied to `<html>` is `light outis-light` — never `dark`.
- `outis-mneme` stays the default theme (`src/app.html` is the authoritative default).
- No Svelte component's markup/classes change for colour reasons. Only the four CodeMirror hosts change, and only to call a shared helper.
- Every rule scoped to `html.outis-light` or `html:is(.outis-mneme, .outis-light)`. Nothing global.
- Shared stylesheet is imported **before** both palette stylesheets in `+layout.svelte`.
- Palette values are fixed by the spec's token tables. Do not re-derive them.
- Accent green never appears in code syntax.

---

### Task 1: Extract the hue-free rules into a shared stylesheet

**Files:**

- Create: `src/outis-theme-shared.css`
- Modify: `src/outis-mneme-theme.css` (remove the extracted rules; keep palette + dark colour rules)
- Modify: `src/routes/+layout.svelte:51` (import the shared file before the mneme file)

**Interfaces:**

- Produces: selector prefix `html:is(.outis-mneme, .outis-light)`; variables `--outis-prose-scale`, `--outis-input-bg`, `--outis-input-fg` (each theme file must define the latter two).

- [x] **Step 1: Move these rules out of `outis-mneme-theme.css` verbatim, changing only the selector prefix**

  The JetBrains Mono `@import`; `font-family` + `--font-sans` + `--font-mono` + the `pre` rule;
  `--radius-*` flattening; `.rounded-full`; the three `[data-sonner-*]` rules and
  `.sonner-loading-bar`; `svg { stroke-linecap: square; stroke-linejoin: miter }`;
  `--outis-mneme-prose-scale` (renamed `--outis-prose-scale`); the `.markdown-prose` /
  `.input-prose` / `-sm` / `-xs` font-size rules; `[class~='text-[0.9375rem]']`; the three
  `.markdown-prose h1/h2/h3` rules; `div[class*='language-'] { font-size: 0.75rem }`; the
  `div[class*='language-'] > div.pt-1.pb-2.px-4` padding rule; the `:focus-visible` suppression
  block; and the four `input:-webkit-autofill` rules plus `input:autofill`.

- [x] **Step 2: Re-point the autofill rules at variables instead of the gray scale**

```css
html:is(.outis-mneme, .outis-light) input:-webkit-autofill,
html:is(.outis-mneme, .outis-light) input:-webkit-autofill:hover,
html:is(.outis-mneme, .outis-light) input:-webkit-autofill:focus,
html:is(.outis-mneme, .outis-light) input:-webkit-autofill:active {
	box-shadow: 0 0 0 1000px var(--outis-input-bg) inset !important;
	-webkit-text-fill-color: var(--outis-input-fg) !important;
	caret-color: var(--outis-input-fg);
	transition: background-color 5000s ease-in-out 0s;
}
```

- [x] **Step 3: Define the two new variables in `outis-mneme-theme.css`**

```css
--outis-input-bg: #090d0c;
--outis-input-fg: #d4ede2;
```

- [x] **Step 4: Import the shared file first**

```js
import '../outis-theme-shared.css';
import '../outis-mneme-theme.css';
```

- [x] **Step 5: Verify `outis-mneme` is unchanged**

Run: `npm run check`
Then load the app on `outis-mneme` and confirm: square corners, JetBrains Mono, 12px reading
area, no focus ring on the composer, square toast corners. Any difference here is a regression,
not a light-theme problem.

- [x] **Step 6: Commit**

```bash
git add src/outis-theme-shared.css src/outis-mneme-theme.css src/routes/+layout.svelte
git commit -m "Split the theme's hue-free rules into a shared stylesheet"
```

---

### Task 2: The light palette stylesheet

**Files:**

- Create: `src/outis-light-theme.css`
- Modify: `src/routes/+layout.svelte` (import it after the shared file)

**Interfaces:**

- Consumes: `--outis-prose-scale`, `--outis-input-bg`, `--outis-input-fg` from Task 1.
- Produces: `html.outis-light` palette; the selection colour `rgba(0, 131, 80, 0.14)` reused by Task 3.

- [x] **Step 1: Write the palette block** — the `--color-gray-*`, `--color-blue-*`,
      `--color-green-*`, `--color-red-*`, `--color-yellow-*`, `--color-white`, `--color-black`,
      `--outis-input-bg`, `--outis-input-fg` values from the spec's token tables, verbatim.

- [x] **Step 2: Write the light-only colour rules** — `body`, `::selection`,
      `.editor-selection`, the `[class~='bg-black']` / `[class~='hover:bg-gray-900']:hover` CTA
      re-skin, the `--tw-prose-*` ladder, inline `code`, the code-block chrome, and the `.hljs-*`
      ring. All from the spec.

- [x] **Step 3: Verify**

Run: `npm run lint:frontend && npm run check`
Expected: PASS.

- [x] **Step 4: Commit**

```bash
git add src/outis-light-theme.css src/routes/+layout.svelte
git commit -m "Add the Outis-Light palette"
```

---

### Task 3: The light CodeMirror theme and a shared theme selector

**Files:**

- Create: `src/lib/codemirror-outis-light-theme.ts`
- Create: `src/lib/codemirror-outis-theme.ts`
- Modify: `src/lib/components/common/CodeEditor.svelte`
- Modify: `src/lib/components/chat/FileNav/CellEditor.svelte`
- Modify: `src/lib/components/chat/FileNav/FileCodeEditor.svelte`
- Modify: `src/lib/components/chat/Messages/OutputEditView.svelte`

**Interfaces:**

- Consumes: the light code ring from the spec.
- Produces: `export const outisLight: Extension[]` and `export function outisEditorTheme(): Extension[]`.

- [x] **Step 1: Write `codemirror-outis-light-theme.ts`** — the same shape as
      `codemirror-outis-mneme-theme.ts` (same tag groups, same rule set), with the light ring, and
      `{ dark: false }` passed to `EditorView.theme`.

- [x] **Step 2: Write the selector helper**

```ts
import type { Extension } from '@codemirror/state';
import { outisMneme } from './codemirror-outis-mneme-theme';
import { outisLight } from './codemirror-outis-light-theme';

export function outisEditorTheme(): Extension[] {
	const cls = document.documentElement.classList;
	if (cls.contains('outis-light')) return outisLight;
	if (cls.contains('dark')) return outisMneme;
	return [];
}
```

- [x] **Step 3: Replace the duplicated ternary in all four hosts** with `outisEditorTheme()`,
      including inside the `MutationObserver` reconfigure paths in `CodeEditor.svelte`,
      `CellEditor.svelte` and `FileCodeEditor.svelte`.

- [x] **Step 4: Verify**

Run: `npm run check`
Then open a chat code block and the Workspace → Tools editor on Outis-Light and on Outis-Mneme,
and switch themes with an editor open — the editor must recolour without a reload.

- [x] **Step 5: Commit**

```bash
git add src/lib/codemirror-outis-light-theme.ts src/lib/codemirror-outis-theme.ts src/lib/components
git commit -m "Give CodeMirror a light Outis theme and one place that picks it"
```

---

### Task 4: Register the theme at the three switch sites

**Files:**

- Modify: `src/app.html` (pre-boot guard + splash background)
- Modify: `src/lib/components/chat/Settings/General.svelte`
- Modify: `src/routes/+layout.svelte` (the `theme:update` handler)

**Interfaces:**

- Consumes: theme id `outis-light`, class list `light outis-light`, meta theme-color `#fafdfc`.

- [x] **Step 1: `app.html`** — add the branch before the `light` branch:

```js
} else if (localStorage.theme === 'outis-light') {
	// The dark themes leave these four set inline, and inline style beats a
	// class selector — clear them so the light palette's CSS can apply.
	['--color-gray-800', '--color-gray-850', '--color-gray-900', '--color-gray-950'].forEach(
		(p) => document.documentElement.style.removeProperty(p)
	);
	document.documentElement.classList.add('light', 'outis-light');
	metaThemeColorTag.setAttribute('content', '#fafdfc');
}
```

and add `html.outis-light #splash-screen { background: #fafdfc; }` to the bottom `<style>` block.

- [x] **Step 2: `General.svelte`** — add `'outis-light'` to `themes`, extend the `themeToApply`
      ternary with `'light outis-light'`, extend the `meta[theme-color]` ternary with `#fafdfc`, add
      the `removeProperty` block, and add the dropdown option **above** the existing Light option.

- [x] **Step 3: `+layout.svelte`** — the same three additions inside the `theme:update` handler.

- [x] **Step 4: Verify**

Run: `npm run lint:frontend && npm run check`
Then walk the acceptance list in `OUTIS_LIGHT_THEME_SPEC.md` § Acceptance, in particular #2:
switch Outis-Mneme → Outis-Light → OLED Dark → Outis-Light and read
`document.documentElement.style.cssText` — it must be empty on Outis-Light.

- [x] **Step 5: Commit**

```bash
git add src/app.html src/lib/components/chat/Settings/General.svelte src/routes/+layout.svelte
git commit -m "Register Outis-Light in the theme switcher"
```
