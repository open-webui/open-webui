# Outis-Mneme Theme — Spec

A new selectable UI theme: a dark, green-accented, monospace, flat-cornered "terminal" look,
added as an option alongside the existing `dark` / `oled-dark` / `light` / `her` themes — not a
replacement for them.

## Goal

Add an `outis-mneme` theme option that a user can pick from Settings → General → Theme, same as
any built-in theme. Selecting it should re-skin the whole app (colors, corner radius, base font)
without touching the ~800 Svelte component files that reference Tailwind utility classes like
`bg-gray-900`, `text-blue-500`, `rounded-lg`, etc.

## Why this is possible without touching components

Open WebUI is on Tailwind CSS v4. Its whole neutral palette is defined once, as CSS custom
properties, in `src/tailwind.css`:

```css
@theme {
  --color-gray-50: oklch(0.98 0 0);
  ...
  --color-gray-950: oklch(0.16 0 0);
}
```

Every `bg-gray-800`, `dark:text-gray-300`, etc. utility across the codebase compiles to
`var(--color-gray-800)` etc., not a literal color. Tailwind v4's own default theme (shipped in
the `tailwindcss` package, not overridden here) defines the rest of the palette the same way —
`--color-blue-500`, `--color-green-500`, `--color-red-500`, `--radius-lg`, and so on are all real,
overridable CSS custom properties, not compile-time constants.

The codebase already proves this pattern works: the built-in `oled-dark` theme is implemented by
overriding 4 of the gray steps (`--color-gray-800/850/900/950`) via inline
`style.setProperty()` calls at theme-switch time (see `src/app.html`, `General.svelte`,
`+layout.svelte`). This spec extends that same mechanism — override more of the palette, via a
proper CSS file instead of inline JS, scoped to a new `html.outis-mneme` class.

## Scope

**In scope** — re-themeable through CSS custom property overrides + one global stylesheet:
- Full neutral scale (`gray-50…950`) → nine-step near-black/green-tinted scale
- Accent scale (`blue-*`, since blue is what ~185 interactive/focus/link utility usages in the
  codebase use as "the accent color") → green scale
- `green-*` itself (already used for ~21 "positive/success" indicators) → same green scale, so it
  stays semantically correct and visually unified with the new accent
- `red-*` (destructive/error) and `yellow-*` (warning) → tuned to close equivalents, keeping their
  existing semantic meaning (still "red = danger", still "yellow = warning")
- Corner radius (`--radius-xs` through `--radius-4xl`, used by `rounded-sm`…`rounded-4xl`,
  445+356+... usages) → `0` (flat). `rounded-full` (316 usages — avatars, circular icon buttons)
  is untouched; it's a fixed 9999px utility, not radius-token-driven, and those are genuine
  circles, not "rounded corners."
- Base font (`html, pre` currently `Inter`/`Vazirmatn`/system-ui stack) → monospace, to match the
  terminal aesthetic

**Out of scope for this pass** (flag if you want them later, each is a separate, larger change):
- `white`/`black` literal utility usages (~1,160 combined) — not overridden. Many of these are
  one-off contrast fixes (badge text, overlay scrims) unrelated to the theme scale; blanket
  override risk is high for low visual payoff. Spot-fix individually later if specific elements
  look wrong.
- Splash screen (`html.her` has bespoke splash-screen CSS in `app.html`; `outis-mneme` does not,
  it reuses the existing dark splash) and favicon/meta theme-color art.
- Per-component structural changes (e.g. an actual sidebar-nav-with-badges layout swap). This
  pass is a **palette + corner + font reskin** of the existing layout, not a layout rebuild.
- A distinct display font for headings (kept to one font, monospace, for the whole UI — simpler,
  lower risk, avoids hunting down every heading-ish element individually).

## Token mapping

Anchor values pulled from an internal reference dark/green terminal palette (bg `#090d0c`,
surface `#0f1512`, card `#141c19`, border `#1a2823`, accent `#2dff8f`, muted `#4a6a5a`, text
`#d4ede2`, danger `#ff4e4e`, warning `#f5c542`), interpolated to fill Tailwind's full step scales:

| Token | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `--color-gray-*` | `#d4ede2` | `#b9d9cb` | `#9dc4b3` | `#7aab98` | `#5c8f7d` | `#4a6a5a` | `#3a5346` | `#2a3d34` | `#1a2823` | `#0f1512` | `#090d0c` |
| `--color-blue-*` (accent) | `#eafff5` | `#d0ffe8` | `#a6ffd2` | `#6ffcb0` | `#4dfa9e` | `#2dff8f` | `#1a8f52` | `#146b3d` | `#0f5230` | `#0c3823` | `#082217` |
| `--color-green-*` | *(same scale as `--color-blue-*` above — one accent, two names)* |
| `--color-red-*` | Tailwind default, only `500`/`600` tuned to `#ff4e4e` / `#e63e3e` |
| `--color-yellow-*` | Tailwind default, only `500`/`600` tuned to `#f5c542` / `#d9a82a` |

`gray-850` (an Open WebUI-specific extra step between 800/900, used for `oled-dark`'s own
overrides) is left as Tailwind computes it from the surrounding scale — not independently themed,
since `outis-mneme` doesn't use the `oled-dark` code path.

Font: `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace` (loaded via Google Fonts
`@import` in the new theme stylesheet — see Integration points below).

## Integration points

Exactly the three places `oled-dark` already touches, plus one new CSS file:

1. **`src/app.html`** (inline boot script, avoids flash-of-wrong-theme) — add an `else if
   (localStorage.theme === 'outis-mneme')` branch: add classes `dark outis-mneme` to
   `documentElement`, set the meta theme-color to `#090d0c`. Also explicitly `setProperty()` the
   four `--color-gray-800/850/900/950` steps here (see "Inline-style hazard" below) so the values
   are correct even before the stylesheet's class rule would otherwise apply.
2. **`src/lib/components/chat/Settings/General.svelte`** — add `'outis-mneme'` to the theme
   picker `<option>` list and to `applyTheme()`'s class bookkeeping (same shape as the
   `oled-dark` branch), plus the same explicit `setProperty()` calls as above.
3. **`src/routes/+layout.svelte`** — mirror the same branch in the desktop-app `theme:update`
   event handler, for parity with the other two entry points (this file's comment literally says
   "mirrors logic from chat/Settings/General.svelte").
4. **New file `src/outis-mneme-theme.css`**, imported once from `src/routes/+layout.svelte`
   (alongside the existing `tailwind.css`/`app.css` imports) — the actual
   `html.outis-mneme { --color-gray-50: ...; ...; font-family: ...; }` block from the token
   mapping above, plus the radius-flattening block. One file, one place to tune later.

No other file needs to change. Every Svelte component keeps its existing `bg-gray-900
dark:text-white rounded-lg` etc. classes exactly as-is; they just resolve to different values
when `html.outis-mneme` is the active scope.

### Inline-style hazard (why step 1/2 also set properties via JS, not just CSS)

`dark` and `oled-dark` both set `--color-gray-800/850/900/950` via **inline style** on
`documentElement` (`style.setProperty(...)`), which has higher CSS specificity than any class
selector. If a user selects "Dark" or "OLED Dark" first and then switches to "Outis-Mneme", those
four inline-set properties would persist and silently override the same four properties defined
in `html.outis-mneme { ... }`, since inline style always wins over a stylesheet rule regardless of
selector specificity. Fix: the `outis-mneme` branch explicitly calls `setProperty()` for those
same four steps with its own values, exactly like `oled-dark` already does — this guarantees
correctness regardless of which theme was active immediately before.

### `<body>` hardcoded literal (found during testing, now fixed)

`src/app.css` has one exception to the "everything is a `var(--color-gray-*))` rule: `body {
background: #fff; color: #000 } .dark body { background: #171717; color: #eee }` is a hardcoded
literal color, not a variable reference. Confirmed via `getComputedStyle` during local testing —
every other surface picked up the theme correctly, but `document.body`'s own background stayed at
Tailwind's stock `#171717` regardless of the `html.outis-mneme` override. Fixed with a direct
`html.outis-mneme body { background: #090d0c; color: #d4ede2 }` rule (specificity naturally wins
over `.dark body`, no `!important` needed).

### `--font-sans` / `--font-mono` tokens (found during testing, now fixed)

The user-menu dropdown (and likely other components using the same pattern) rendered in Inter
instead of JetBrains Mono, despite the `html.outis-mneme` rule setting `font-family` directly.
Root cause: that dropdown's wrapper has an explicit Tailwind `font-sans` utility class, which
resolves through `var(--font-sans)` — a *different* token than the one we set. Components that
just inherit typography pick up the `html`-level `font-family`; components that explicitly opt
into `font-sans`/`font-mono` utilities resolve through those tokens instead, bypassing the
inherited value. Fixed by also overriding `--font-sans` and `--font-mono` to the same JetBrains
Mono stack — same "override the token, not each component" approach as everything else in this
spec, and it should now cover every remaining component using either utility, not just this one
dropdown.

### Reading-area font size (found from live use, now fixed)

The chat response text (`.markdown-prose`, forced to `0.9375rem`/15px via a Tailwind `!important`
arbitrary value in `app.css`) read noticeably larger once switched to JetBrains Mono, even though
the nominal size didn't change. Monospace faces generally read bigger/wider than a proportional
face like Inter at the same rem value — fixed-width glyphs and a taller x-height take up more
visual room. Sized down to `0.75rem`/12px specifically for `.markdown-prose` under
`html.outis-mneme` (needs `!important` to beat the `!text-[0.9375rem]` it's overriding) — an
intermediate `0.8125rem`/13px pass still read too big in live use, 12px matched the reading
density most monospace-first terminal/dashboard UIs settle on. Scoped to the reading area only — not a change to the
font-size scale generally.

### Redundant follow-up-question tooltip (found from live use, now fixed)

`FollowUps.svelte` (the suggested-next-question chips shown after a response) wrapped every chip
in a `Tooltip` showing the exact same text as the button label, unconditionally — not only when
the label was actually truncated. Since the button already shows the text, the tooltip just
repeated it on hover. This isn't a CSS/token issue like everything else in this spec — it's a
small, out-of-band Svelte component change (removed the `Tooltip` wrapper, kept the button and its
`line-clamp-1` truncation). Noted here for completeness even though it's unrelated to the theme's
color/type/radius scope.

## Testing plan

1. `npm install` (fresh checkout, no `node_modules` yet), `npm run dev`.
2. Confirm the theme dropdown lists "Outis-Mneme" and selecting it doesn't throw.
3. Visual pass over: chat view (message bubbles, input bar, model selector), sidebar (nav, chat
   list, buttons), Settings modal (tabs, inputs, toggles), a modal/dialog (rounded corners should
   read as flat), any visible focus rings/links (should read green, not blue).
4. Switch **Dark → Outis-Mneme** and **OLED Dark → Outis-Mneme** specifically — confirms the
   inline-style hazard above is actually handled, not just working by accident on first load.
5. Confirm `dark`/`oled-dark`/`light`/`her`/`system` still work unmodified — this is an addition,
   not a replacement, so regressing the existing themes is the one thing that must not happen.
6. Reload the page after selecting Outis-Mneme — confirm no flash of the wrong theme (the
   `app.html` boot script is what prevents this).

## Acceptance

Selecting "Outis-Mneme" from Settings turns the whole app dark-near-black with a single green
accent, flat (non-rounded) corners everywhere except genuine circles (avatars, dots,
circular icon buttons), and a monospace UI font — while every other theme option continues to
work exactly as it did before this change.
