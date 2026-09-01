# Outis-Light Theme — Spec

A light counterpart to `outis-mneme`: the same monospace, flat-cornered, one-accent identity,
rebuilt for a light ground. Added as a fifth selectable theme alongside
`dark` / `oled-dark` / `light` / `her` / `outis-mneme` — it replaces none of them, and
`outis-mneme` stays this build's default.

## Goal

Selecting **Outis-Light** in Settings → General → Theme re-skins the whole app to a light
version of the Outis identity, without touching the ~800 Svelte component files that reference
Tailwind utility classes. Someone who knows `outis-mneme` should recognise this as the same
theme with the lamp turned around — not as "the stock light theme with green bits".

## Design direction

`outis-mneme` is a phosphor tube: light is _emitted_, so the ground is near-black and every
colour is a glow on top of it. Inverting that literally (bright green on white) is unreadable
and reads as a different product.

The light counterpart is the other half of the same lineage: **ink on paper** — the line-printer
page, the plotted engineering drawing, the pen recorder. Same hue family, same discipline,
figure and ground exchanged.

Three consequences drive every value below:

1. **The pigments swap places, they don't change.** `outis-mneme`'s darkest surface
   (`#0f1512`) is almost exactly this theme's darkest ink (`#0e1913`). The neutral scale is one
   green-tinted hue (OKLCH H162), read from the other end.
2. **The paper is cool, not cream.** Warm cream with a serif is the reflex light-theme move and
   would break the family resemblance — `outis-mneme` has no warm neutrals anywhere. The ground
   is `#fafdfc`, a faint green-grey, so a screenshot of either theme is obviously the same
   product.
3. **Every role keeps its meaning, only its lightness flips.** Green still means _interactive_
   and nothing else. Amber still means _heading_, warm against cool, separating by hue rather
   than by another near-black tone. Code still gets four hues on one perceptual plane, so no
   token outshines its neighbour.

The one place this theme is louder than a stock light theme, and deliberately so: primary
buttons are the accent green rather than black-on-white, exactly as `outis-mneme` makes them
accent green rather than white-on-black. In both themes a primary action is _the_ accent colour.

## Why this is possible without touching components

Identical mechanism to `outis-mneme` — see `OUTIS_MNEME_THEME_SPEC.md` § "Why this is possible
without touching components". Every `bg-gray-50`, `text-blue-500`, `rounded-lg` compiles to a
`var(--color-*)` / `var(--radius-*)` reference, so a stylesheet scoped to `html.outis-light`
re-points the whole palette.

The differences from `outis-mneme` come from one fact: **this theme does not add the `dark`
class.** It applies `light outis-light`. That flips which half of the codebase is live:

|                        | `outis-mneme` (`dark outis-mneme`)      | `outis-light` (`light outis-light`)                |
| ---------------------- | --------------------------------------- | -------------------------------------------------- |
| Active utilities       | `dark:*` variants                       | base utilities                                     |
| Prose vars             | `--tw-prose-invert-*`                   | `--tw-prose-*`                                     |
| Main surface literal   | `dark:bg-black`, `dark:bg-white` scrims | `bg-white` (118 usages) — the ground itself        |
| Primary CTA half       | `dark:bg-white dark:text-black`         | `bg-black text-white`                              |
| Body rule in `app.css` | `.dark body { background:#171717 }`     | `body { background:#fff; color:#000 }`             |
| CodeMirror             | `outisMneme` theme                      | previously `[]` (stock light) — needs `outisLight` |
| highlight.js           | `github-dark.min.css` re-coloured dark  | same import, re-coloured **light**                 |

So the two themes share all their _shape_ (font, radius, sizes, focus behaviour) and share none
of their _colour_. That split is the file structure below.

## File structure

`outis-mneme-theme.css` currently mixes both. This spec extracts the shape half once rather
than copying ~120 lines of it into a second theme, which is how the size-inconsistency bug in
`OUTIS_MNEME_CONSISTENCY_SPEC.md` Finding 1 happened in the first place.

| File                                              | Responsibility                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/outis-theme-shared.css` _(new)_              | Hue-free rules for **both** themes, selected by `html:is(.outis-mneme, .outis-light)`: JetBrains Mono, radius flattening, `rounded-full`, sonner corners, SVG stroke caps, the whole prose/reading-chrome size scale, editor focus-ring suppression, code-block padding alignment, autofill (via two per-theme variables). |
| `src/outis-mneme-theme.css` _(trimmed)_           | Dark palette + dark-only colour rules only.                                                                                                                                                                                                                                                                                |
| `src/outis-light-theme.css` _(new)_               | Light palette + light-only colour rules.                                                                                                                                                                                                                                                                                   |
| `src/lib/codemirror-outis-light-theme.ts` _(new)_ | The light CodeMirror theme + highlight style.                                                                                                                                                                                                                                                                              |
| `src/lib/codemirror-outis-theme.ts` _(new)_       | `outisEditorTheme()` — returns the extension array matching the classes currently on `<html>`. Replaces the `isDark ? outisMneme : []` ternary duplicated across 4 editor components.                                                                                                                                      |

`:is()` takes the specificity of its most specific argument, so `html:is(.outis-mneme, .outis-light) .x`
has exactly the specificity `html.outis-mneme .x` had. Nothing in the mneme theme changes weight.
The shared file is imported **before** both palettes so a palette can still win a tie.

## Token mapping

Neutral and accent ramps are OKLCH-derived, in gamut, with the contrast of each rung measured
against the paper (`#fafdfc`). Neutral holds `src/tailwind.css`'s own lightness ramp — so every
existing light-mode layout keeps the contrast relationship it was designed with — and adds
chroma at H162.

### Ground

| Token           | Value     | Note                                                                                                                                                                                         |
| --------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--color-white` | `#fafdfc` | The paper. Overridden here (mneme deliberately does not) because in light mode `bg-white` is the app's ground, not a scrim; leaving it pure white against a tinted `gray-50` reads as a bug. |
| `--color-black` | `#070e0a` | Green-black ink, not `#000`. Also tints `bg-black/60` modal scrims into the family.                                                                                                          |

### `--color-gray-*` (H162)

| 50        | 100       | 200       | 300       | 400       | 500       | 600       | 700       | 800       | 850       | 900       | 950       |
| --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- |
| `#eff5f2` | `#e4ede8` | `#d7e3dd` | `#c3d2ca` | `#a7bab0` | `#8ca195` | `#596f63` | `#40544a` | `#27372f` | `#1c2a22` | `#0e1913` | `#070e0a` |

Contrast on paper: 1.08 / 1.17 / 1.29 / 1.53 / 1.99 / 2.68 / **5.29** / **7.94** / 12.26 / 14.62 / 17.58 / 19.07.
`gray-600` is the first rung that carries body text, matching stock light mode's usage.

### `--color-blue-*` = `--color-green-*` (accent, H158)

| 50        | 100       | 200       | 300       | 400       | 500       | 600       | 700       | 800       | 900       | 950       |
| --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- |
| `#e6fcee` | `#cbf8dc` | `#a2f0c2` | `#6de3a4` | `#00bc76` | `#008350` | `#006e43` | `#005a36` | `#00472a` | `#00351e` | `#002412` |

`500` is anchored at **4.70:1** on paper — the AA floor for the links, focus rings and
`bg-blue-500 text-white` badges that use it — and `500 → 950` is an even OKLCH lightness ramp
(ΔL ≈ 0.062/step) with chroma tapering alongside, the same correction
`OUTIS_MNEME_CONSISTENCY_SPEC.md` Finding 2 applied to the dark ramp. `600` (6.20:1) carries
hover states and filled buttons.

Unlike `outis-mneme`, `bg-blue-500 text-white` needs **no** override here: paper text on
`#008350` is 4.70:1. The mneme rule that flips that pairing to dark text is dark-only and is
staying in the mneme file.

### Danger / warning

| Token                | Value     | Contrast on paper                          |
| -------------------- | --------- | ------------------------------------------ |
| `--color-red-500`    | `#d2383a` | 4.70:1                                     |
| `--color-red-600`    | `#b91c26` | 6.30:1                                     |
| `--color-yellow-500` | `#d79700` | 2.47:1 — icons/fills, as in stock Tailwind |
| `--color-yellow-600` | `#b47d00` | 3.49:1                                     |

Same reasoning as mneme: red stays red, yellow stays yellow, both retuned so they sit on paper
instead of on near-black.

### Reading area (`--tw-prose-*`, the non-inverted half)

One tonal ladder, mirroring the dark theme's role order — headings darkest, then bold, then
body, then quiet:

| Role                                | Value                  | Contrast                                              |
| ----------------------------------- | ---------------------- | ----------------------------------------------------- |
| headings                            | `#543900`              | 10.46:1 — printed ochre, warm against the cool ground |
| bold                                | `#37473f`              | 9.61:1                                                |
| body                                | `#3f5047`              | 8.38:1                                                |
| links                               | `#007548`              | 5.64:1                                                |
| lead / quotes / captions / counters | `#607369`              | 4.94:1                                                |
| bullets                             | `#76897f`              | 3.63:1                                                |
| hr / quote / th borders             | `#d7e3dd` (`gray-200`) | —                                                     |
| td borders                          | `#e4ede8` (`gray-100`) | —                                                     |

Inline `code` gets an explicit rule for the same reason it does in mneme (`tailwind.config.js`
sets typography's `code: false`): `#3a4d43` on `#e4ede8`, one step off the code block's own
ground so a snippet in a sentence and a snippet in a block are the same colour.

### Code (CodeMirror + highlight.js, both paths)

Four hues on **one** OKLCH plane, equalised by contrast rather than by lightness so no category
shouts. Ground is `gray-50` `#eff5f2`.

| Role                              | Value     | Contrast | Hue                     |
| --------------------------------- | --------- | -------- | ----------------------- |
| keywords                          | `#105f31` | 7.03:1   | H152                    |
| names — functions, types, classes | `#005b6c` | 7.01:1   | H215                    |
| literal values                    | `#5f4687` | 7.01:1   | H300                    |
| strings, regexps                  | `#6f4c00` | 7.02:1   | H78 (the only warm hue) |
| identifiers (reading baseline)    | `#3a4d43` | 8.19:1   | H162                    |
| operators, punctuation            | `#5f7368` | 4.59:1   | H162                    |
| comments                          | `#677c71` | 4.05:1   | H162                    |
| gutter line numbers               | `#7c8f84` | 3.11:1   | H162                    |
| deleted / invalid                 | `#b63032` | 5.50:1   | H25                     |

The ring spans 7.01–7.03:1 — a 0.02 spread, tighter than the dark theme's 8.4–8.9. As in mneme,
**the accent green never appears in syntax**: it marks interaction (caret, selection, focus,
links) and nothing in a code block is interactive.

Selection / active-line, mirroring mneme's `rgba(45, 255, 143, 0.16)` / `0.05`:
`rgba(0, 131, 80, 0.14)` and `rgba(0, 131, 80, 0.05)`. One value shared by CodeMirror's
selection layer, `::selection`, and `.editor-selection`, so all three read as one colour.

## Light-only colour rules

These have no mneme equivalent — they exist because base (non-`dark:`) utilities are live.

1. **`body`** — `app.css`'s `body { background:#fff; color:#000 }` is a hardcoded literal, the
   light-mode twin of the `.dark body` rule mneme already overrides. → paper / ink.
2. **Primary CTA** — the `bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black`
   pattern (84 `bg-black` token usages, 81 of those files also carrying `dark:bg-white`).
   `[class~='bg-black']` → `blue-600`; `[class~='hover:bg-gray-900']:hover` → `blue-700`.
   `[class~=]` matches the exact token, so `bg-black/60` scrims (64+ usages) are untouched.
3. **Code-block chrome** — `CodeBlock.svelte` paints six surfaces `bg-white dark:bg-black`; in
   light mode that's the paper, leaving a two-tone seam against the `gray-50` code body. Scoped
   to the `language-*` container, → `gray-50`. Its `text-black` label/controls → `gray-600`, so
   the code stays the brightest thing in its own block (mneme drops the same chrome to
   `gray-300` for the same reason).
4. **highlight.js** — `github-dark.min.css` is imported unconditionally by `CodeBlock.svelte`,
   so a light theme gets dark code blocks while a response streams. Re-coloured to the light
   ring above, matching the CodeMirror theme so a block does not recolour itself as it finishes
   streaming.
5. **Splash screen** — `app.html`'s `#splash-screen { background:#fff }` → paper, so the very
   first paint is not a white flash.

## Integration points

Every place `outis-mneme` is registered gets an `outis-light` sibling. The class list applied is
`light outis-light` (no `dark`).

1. `src/app.html` — the pre-boot FOUC guard: an `else if (localStorage.theme === 'outis-light')`
   branch adding `light outis-light`, clearing the four inline `--color-gray-*` properties that
   `dark`/`oled-dark`/`outis-mneme` may have left behind, and setting `meta[theme-color]` to
   `#fafdfc`. The default stays `outis-mneme`.
2. `src/lib/components/chat/Settings/General.svelte` — `themes` array, the `themeToApply`
   ternary (`'light outis-light'`), the `meta[theme-color]` ternary, the inline-property block,
   and a `<option value="outis-light">` in the dropdown.
3. `src/routes/+layout.svelte` — the same three additions in the `theme:update` desktop-event
   handler, plus `import '../outis-theme-shared.css'` and `import '../outis-light-theme.css'`.
4. The four CodeMirror hosts — `common/CodeEditor.svelte`, `chat/FileNav/CellEditor.svelte`,
   `chat/FileNav/FileCodeEditor.svelte`, `chat/Messages/OutputEditView.svelte` — switch from
   `isDark ? outisMneme : []` to the shared `outisEditorTheme()` helper.

### Inline-style hazard

`oled-dark` and `outis-mneme` set `--color-gray-800/850/900/950` as **inline** properties on
`<html>`, and inline style beats any class selector. A theme that only adds a class inherits
whatever the previous theme left inline. `outis-mneme` handles this by setting its own four
values inline; `outis-light` instead **removes** all four properties at each of the three switch
sites, so its stylesheet's own `--color-gray-*` values apply with nothing overriding them.
See `OUTIS_MNEME_THEME_SPEC.md` § "Inline-style hazard".

## Found during implementation (now fixed)

These three were not in the original plan; all were caught by driving the built app in a real
browser rather than by reading the CSS.

### The keyboard focus ring was never themed — in _either_ theme

`app.css` writes the a11y focus ring as `outline: 2px solid theme(--color-blue-500)`. Tailwind
v4's `theme()` _function_ resolves at build time to a literal: the compiled CSS reads
`outline: 2px solid oklch(62.3% .214 259.815)`. Unlike every `var(--color-*)` reference in the
app, it does not follow a theme's override — so `outis-mneme` has been painting a stock-blue ring
on every focused button, link and menu item since it shipped, the one piece of interactive chrome
outside its accent hue. Fixed in `outis-theme-shared.css` by re-pointing `outline-color` only, so
app.css keeps its width, offset, and its deliberate high-contrast ring on editors. Verified by
keyboard: the ring is now `#008350` on Outis-Light and `#2dff8f` on Outis-Mneme.

### The Outis mark is drawn in the dark theme's accent

`static/favicon.png` is a single flat fill of `#2dff8f` — 1.3:1 on paper, so the sign-in logo,
the assistant's avatar on every reply, the notification toast icon and the model-editor default
all but vanished. `static/splash.png` needed nothing: it is already drawn in `#090d0c` ink, which
is the asset `app.html`'s light branch picks. Since the mark is one flat colour on transparency,
`filter: brightness(0.431)` maps it exactly onto blue-600 rather than approximately, which avoids
shipping a second copy of the artwork to keep in sync. It ships at two paths that are both live
(`/static/favicon.png` from components, `/favicon.png` from `safeImageUrl.ts`'s
`PLACEHOLDER_IMAGE`), so the selector matches the suffix.

### There are two filled-control idioms, not one

The plan covered `bg-black hover:bg-gray-900 … dark:bg-white`. A second one exists —
`bg-gray-900 hover:bg-black … dark:bg-gray-100` — behind Save & Create in the Tool/Skill/Function
editors, ConfirmDialog's confirm, AskUserCard's answers, the Save/Cancel pair on an edited
message, `Switch`'s ON state, SyncStatsModal's progress bar, and ModelEditor's avatar badge. All
14 bare `bg-gray-900` usages are filled controls, never panels, so both idioms are re-skinned
together and a filled control means one thing across the theme.

`outis-mneme` has the mirrored gap: its `dark:bg-gray-100` / `dark:bg-gray-200` half is still
stock, so Save & Create renders pale mint there while its other CTAs render accent. Left alone
rather than changing the dark theme's appearance as a side effect of adding a light one —
**a follow-up if you want the two idioms unified in Outis-Mneme too.**

## Non-goals

- Changing the default theme. `outis-mneme` stays default; `outis-light` is opt-in.
- A light `high-contrast` variant. `app.css`'s existing `html.high-contrast:not(.dark)` rules
  already apply, and the shared focus-ring suppression yields to them via `:not(.high-contrast)`
  exactly as it does for mneme.
- Re-theming `her`, `light`, `dark`, `oled-dark`, or any layout/structural change. This is a
  palette + corner + font reskin, as mneme was.
- Light splash-screen artwork. The existing `splash.png` is already the light-mode asset.

## Acceptance

1. Settings → General → Theme lists **Outis-Light**; selecting it re-skins the app immediately,
   and the choice survives a reload with no white flash on first paint.
2. Switching Outis-Mneme → Outis-Light → OLED Dark → Outis-Light in sequence leaves no stale
   inline `--color-gray-*` values (verified by reading `document.documentElement.style`).
3. `outis-mneme` renders identically before and after the shared-file extraction.
4. Body text on paper measures ≥ 8:1; links, focus rings and accent badges ≥ 4.5:1; every code
   token ≥ 4:1 with the four syntax hues within 0.1 of each other.
5. A code block does not change colour when a streaming response finishes (highlight.js and
   CodeMirror agree).
6. Corners are square, the font is JetBrains Mono, and green is the only accent hue anywhere
   outside code syntax.
7. `npm run lint:frontend` and `npm run check` pass.

## Verification record

Driven against a production `npm run build`, served with a stub backend, in headless Chromium
(Playwright). Every item below was measured, not eyeballed.

| Check                                                 | Result                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Acceptance 1 — theme listed, applies, survives reload | Dropdown reads `⚙️ System / 🌑 Dark / 🌃 OLED Dark / 🟢 Outis-Mneme / 🟩 Outis-Light / ☀️ Light`; `<html class="light outis-light">`, body `#fafdfc`, meta theme-color `#fafdfc`, applied pre-boot with no flash                                                                                                                                                       |
| Acceptance 2 — no stale inline properties             | Outis-Mneme → Outis-Light → OLED Dark → Outis-Light → Dark → Outis-Light through the real Settings dropdown; on every Outis-Light step `documentElement.style` holds only the app's own `--sidebar-width` / `--app-text-scale`                                                                                                                                         |
| Acceptance 3 — Outis-Mneme unchanged                  | Rule-level diff of the split: every rule byte-identical apart from the three intended renames. Screenshots of the chat home and the CodeMirror tools editor, before vs. after, **byte-identical PNGs**                                                                                                                                                                 |
| Acceptance 4 — contrast                               | Body 8.38:1, headings 10.46:1, links 5.64:1, accent-500 4.70:1, syntax ring 7.01–7.03:1 (0.02 spread), comments 4.05:1                                                                                                                                                                                                                                                 |
| Acceptance 5 — no recolour when streaming ends        | highlight.js and CodeMirror share one palette; chrome, spacer and collapsed body all resolve to `rgb(239,245,242)` against CodeBlock's real DOM shape, in both themes                                                                                                                                                                                                  |
| Acceptance 6 — corners, font, accent                  | `border-radius: 0px`, `JetBrains Mono`, primary CTA `rgb(0,110,67)` on paper text, focus ring `rgb(0,131,80)`                                                                                                                                                                                                                                                          |
| Acceptance 7 — build and checks                       | `npm run build` passes. `npm run check` adds **zero** errors in the new/changed files (the repo has ~7,787 pre-existing ones, and `CodeEditor.svelte` actually loses one). `npm run lint:frontend` crashes inside `@typescript-eslint/no-unused-vars` on `AskUserCard.svelte` — reproduced identically on the unmodified baseline, so it is pre-existing and unrelated |
| Stock themes unaffected                               | `light` still renders `#ffffff` / `#000000` in `-apple-system`                                                                                                                                                                                                                                                                                                         |
