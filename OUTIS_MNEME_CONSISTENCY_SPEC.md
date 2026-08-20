# Outis-Mneme Theme — Consistency Spec

A follow-up audit of `OUTIS_MNEME_THEME_SPEC.md`. That spec re-skinned the app correctly at the
mechanism level (variable overrides, one file, no component churn) and already fixed several
real bugs found from live use (prose glare, reading-area size, code-block seams). This pass looks
past "does it work" to "does it hang together as one system," against the three symptoms
reported: **font-size consistency**, **code color-coding**, **uneven font brightness**. All
numbers below are computed from the actual values in `src/outis-mneme-theme.css` and
`src/lib/codemirror-outis-mneme-theme.ts` (WCAG relative-luminance contrast, OKLCH lightness/chroma
via the sRGB→OKLab transform) — not eyeballed. Script used:
`/private/tmp/.../scratchpad/contrast.py` (ephemeral, not part of this diff).

## Finding 1 — Font-size fix was applied once, not systemically

**Root cause.** JetBrains Mono renders visibly larger than Inter at an equal `rem` size (fixed
width + taller x-height). The original spec found this in `.markdown-prose` and compensated:
`0.9375rem` (15px) → `0.75rem` (12px), a **0.8× correction ratio**, validated live. That fix is
scoped to exactly one selector.

**The problem.** Five other selectors carry the identical "sized for Inter, now rendering in
JetBrains Mono" defect and were left untouched:

| Selector | Base size (unthemed) | Used by | Corrected? |
|---|---|---|---|
| `.markdown-prose` | `0.9375rem` (15px) | chat response body | ✅ `0.75rem` |
| `.input-prose` | `0.9375rem` (15px) | **the chat compose box** (`RichTextInput.svelte`) | ❌ untouched |
| `.markdown-prose-sm` | `text-sm` (14px) | `ChangelogModal`, `CitationModal`, `Valves`, `NoteEditor` | ❌ untouched |
| `.markdown-prose-xs` | `text-xs` (12px) | `Valves` (tool/function descriptions) | ❌ untouched |
| `.input-prose-sm` | `text-sm` (14px) | `NoteEditor` | ❌ untouched |

The most visible instance: the box you type into (`.input-prose`, still 15px) sits directly
**below** the response you just read (`.markdown-prose`, 12px) in the same view, in the same font,
at visibly different sizes — nothing else about their content explains why one should read larger
than the other. Citations, tool valve descriptions, and notes have the same "still full-size Inter
measurements, now rendered in a wider font" problem one level removed from the main thread, so it
reads as scattered rather than obviously wrong.

Separately: the base Tailwind type scale (`text-xs`/`text-sm`, 1,217 + 668 call sites across
`src/lib/components`) was **not** touched, and that's very likely correct to leave alone — sidebar,
buttons, menus, settings chrome reading a bit larger/blockier in a monospace face is a legitimate
part of the "terminal UI" aesthetic the theme is going for, not a bug. The bug is narrower than
"the app feels big" — it's that a hand-picked correction exists for exactly one reading-density
class and stops at its nearest siblings, so message-in and message-out don't match, and the
overlay panels that echo prose (citations, notes, valve docs) don't match the thread they're
attached to.

**Fix.** Promote the 0.8× ratio from a one-off literal to a shared token, and apply it to every
prose-family class, not just the one that was live-tested:

```css
html.outis-mneme {
	/* JetBrains Mono reads ~20% larger than Inter at equal rem (validated: 15px felt right
	   at 12px live). One ratio, applied everywhere text is sized for the font it no longer is. */
	--outis-mneme-prose-scale: 0.8;
}

html.outis-mneme .markdown-prose,
html.outis-mneme .input-prose {
	font-size: calc(0.9375rem * var(--outis-mneme-prose-scale)) !important; /* 12px */
}

html.outis-mneme .markdown-prose-sm,
html.outis-mneme .input-prose-sm {
	font-size: calc(0.875rem * var(--outis-mneme-prose-scale)) !important; /* 11.2px */
}

html.outis-mneme .markdown-prose-xs {
	font-size: calc(0.75rem * var(--outis-mneme-prose-scale)) !important; /* 9.6px */
}
```

Verify live at: the compose box against a rendered response (should now match), `NoteEditor`, the
citation modal, and a tool's Valves panel. If 11.2px/9.6px read too small in practice the way the
original 13px pass did, that's exactly the kind of thing the previous round of live-testing
existed to catch — tune the one `--outis-mneme-prose-scale` number, not four separate literals.

## Finding 2 — The accent ramp has a brightness cliff; the neutral ramp doesn't

**Method.** Converted both scales to OKLCH and measured the lightness (`L`) step between adjacent
stops — the same axis Tailwind's own stock gray scale is authored on (`src/tailwind.css` defines
gray 50→950 directly in `oklch(...)`, evenly enough that no step exceeds `L`≈0.18).

Outis-Mneme's neutral scale is fine — steps range `0.029`–`0.114`, comparable to stock Tailwind's
`0.02`–`0.18`. The accent scale (`--color-blue-*`/`--color-green-*`, the app's one interactive
hue) is not:

| step | hex | OKLCH `L` | Δ`L` from previous | contrast vs `#090d0c` |
|---|---|---|---|---|
| 50–500 | `#eafff5`…`#2dff8f` | `0.982` → `0.880` | avg **0.02/step** | `14.4–18.7:1` |
| **500→600** | `#2dff8f` → `#1a8f52` | `0.880` → `0.574` | **`−0.306`** | `14.7:1` → `4.7:1` |
| 700–950 | `#146b3d`…`#082217` | `0.467` → `0.228` | avg `0.08/step` | `3.0:1` → `1.2:1` |

Steps 50–500 are compressed into a near-max-brightness plateau; one step later the ramp cliffs by
`0.306` in `L` — **2.7×–10× every other step in either scale** — then resumes a normal-looking
taper. This is `--color-blue-*`/`--color-green-*`, which the spec deliberately keeps as a full
11-step Tailwind scale (not just the one hero `500` shade) so that every existing `blue-600`,
`hover:bg-blue-700`, `border-green-600`, etc. across the codebase still resolves through it —
confirmed 5 direct `text-blue-600`/`text-blue-700` usages in `src/lib/components`, plus whatever
`bg-`/`border-`/`hover:` variants exist at those steps. Any of them will render markedly dimmer
than the `500` used for the primary links/focus rings/buttons, with nothing perceptually
in-between — which reads as "the accent color is inconsistent" rather than as an intentional
shade progression.

**Fix — worked example.** Re-derive the ramp as one continuous curve in OKLCH instead of two
plateaus stitched together: keep `500` (`L=0.880`, the validated hero accent used for links/focus)
and `950` (`L=0.228`, already serving as a near-background tint) as fixed anchors, and space
`600`–`900` evenly between them (`ΔL≈0.130/step`) with chroma tapering alongside lightness instead
of dropping in one jump:

| step | target `L` | target `C` | derived hex | contrast vs `#090d0c` | was |
|---|---|---|---|---|---|
| 500 | 0.880 | 0.217 | `#2dff8f` (unchanged) | 14.7:1 | 14.7:1 |
| 600 | 0.750 | 0.190 | `#00cf76` | **9.5:1** | 4.7:1 |
| 700 | 0.619 | 0.155 | `#00a05a` | **5.8:1** | 3.0:1 |
| 800 | 0.489 | 0.120 | `#037340` | 3.3:1 | 2.1:1 |
| 900 | 0.358 | 0.085 | `#064928` | 1.9:1 | 1.5:1 |
| 950 | 0.228 | 0.039 | `#0b2214` (≈unchanged) | 1.2:1 | 1.2:1 |

`600` and `700` are the pair that matters most in practice (the conventional "default → hover"
Tailwind step for buttons/links) — this redistribution moves `700` from `3.0:1` (fails WCAG AA for
any text size) to `5.8:1` (passes AA for normal text), and `600` from a middling `4.7:1` to a
comfortable `9.5:1`, without touching the `500` value already validated live. All five derived
hexes above are in-gamut sRGB (verified via the OKLab round-trip). Treat the exact hex values as a
starting point, not final — the original spec's own pattern was to compute a first pass, then
adjust from a live look (e.g. the 13px→12px correction); do the same here before committing.

## Finding 3 — Three unrelated "brightest text" values compete on screen

Beyond the accent cliff, there isn't one shared ceiling for "this is the brightest text in the
UI" — there are three, from three different unrelated sources, often visible in the same view:

| Source | Value | Contrast vs bg | Where |
|---|---|---|---|
| Literal `white` / `dark:text-white` (**explicitly out of scope** in the original spec's "~1,160 combined" note) | `#ffffff` | ~20:1 | 368 usages across `src/lib/components` |
| Theme's own `gray-50`/`gray-100` (via `dark:text-gray-100/200/300`) | `#d4ede2` / `#b9d9cb` | 15.8:1 / 12.9:1 | 190+ files |
| Hand-tuned prose "headings" role (a deliberately different hue — amber, not mint) | `#ebd0a7` | 13.1:1 | chat response `h1`–`h3` |

None of these three is wrong in isolation — the prose ladder in particular was carefully built
(headings/strong/body/quiet as a deliberate contrast progression, documented in
`outis-mneme-theme.css` lines 127–199). The inconsistency is that they don't share a source of
truth: a sidebar label in un-themed pure white, a chat heading in warm amber, and body copy in
cool mint-gray can all be on screen together with no common ceiling relating them, which is a
second, independent contributor to "uneven brightness" — distinct from the accent-ramp cliff in
Finding 2 and not fixable by the same change.

This was called out as an explicit scope cut in the original spec ("Spot-fix individually later if
specific elements look wrong") — this is that follow-up.

**Implemented, without editing any of the 159 component files.** `--color-white` is itself a real,
overridable Tailwind v4 token (`node_modules/tailwindcss/theme.css`) — but overriding it globally
would retint every `bg-white`/`border-white` scrim and badge too, which is exactly the blanket risk
the original spec avoided (1,160 combined usages, most of them legitimately literal). Targeting the
class tokens directly instead:

```css
html.outis-mneme [class~='text-white'],
html.outis-mneme [class~='dark:text-white'] {
	color: var(--color-gray-50);
}
```

`[class~=...]` matches the exact class token in the `class` attribute, not a substring — so this
touches only elements actually carrying `text-white`/`dark:text-white`, leaves `bg-white`/
`border-white`/`ring-white` untouched, and needs no `!important` (wins on specificity the same way
every other rule in this file does — see Finding 4's correction). All three "brightest text" values
now converge on one ceiling: the theme's own `gray-50` (15.8:1), not a separate unthemed 20:1.

## Finding 4 — Code-color scheme is solid; retracted a false alarm

The CodeMirror ring (`codemirror-outis-mneme-theme.ts`) and the highlight.js rules
(`outis-mneme-theme.css` lines 219–297) use **identical hex values** for all six token roles
(keyword `#8cc099`, name `#74bed0`, literal `#b8a6dc`, string `#cdab78`, identifier `#b9d9cb`,
comment `#71867b`) — confirmed by direct comparison, not assumed. A code block does not recolor
itself as it finishes streaming and switches rendering paths. The four-hue ring is genuinely
well-designed: one OKLCH lightness/chroma budget (`L 0.76 / C 0.078`), only hue varying, so no
token category outshines another (`8.4–8.9:1` band, confirmed). **This part does not need
touching.**

**Correction (this pass originally flagged a gap here that doesn't hold up):** the first draft of
this spec claimed `github-dark.min.css`'s compound selectors (e.g. `.hljs-variable.language_`,
used for `self`/`this`/`super`) out-specificity `outis-mneme-theme.css`'s plain `.hljs-variable`
rule and win regardless of load order. That compared the two rules' class/type counts incorrectly
— every rule in `outis-mneme-theme.css` is written as `html.outis-mneme .hljs-variable`, not bare
`.hljs-variable`. That `html.outis-mneme` prefix adds one class *and* one type selector that
`github-dark`'s bare, unscoped rules don't have, e.g.:

| selector | classes | types | specificity |
|---|---|---|---|
| `html.outis-mneme .hljs-variable` (this theme) | 2 (`.outis-mneme`, `.hljs-variable`) | 1 (`html`) | `(0,2,1)` |
| `.hljs-variable.language_` (github-dark) | 2 | 0 | `(0,2,0)` |

`(0,2,1) > (0,2,0)` — the theme's rule wins outright, deterministically, independent of stylesheet
import order. Checked every compound selector github-dark's theme defines (`.hljs-variable.language_`,
`.hljs-title.class_.inherited__`, the `.hljs-meta .hljs-keyword`/`.hljs-meta .hljs-string`
descendant rules) against outis-mneme's corresponding rule the same way — the `html.outis-mneme`
prefix wins every one. No fix needed; not implementing the `!important`/explicit-compound-selector
change this spec originally proposed here, since there's nothing for it to guard against.

## Finding 5 — Code-block font size vs. prose (found live, now fixed)

Live-testing the fixes above (real backend, real chat history, not the static harness) surfaced a
sixth mismatch the original audit didn't cover: rendered code blocks computed to `14px`, next to
`12px` prose. Two independent sources, both outside anything this theme had touched:

- `@codemirror/view`'s own library `baseTheme` hardcodes `.cm-editor { font-size: 14px }` —
  nothing in this repo sets it; it ships that way from the package itself.
- The highlight.js (streaming) path never gets its own font-size — it inherits `text-sm` (14px)
  from `CodeBlock.svelte`'s `language-{lang}` wrapper.

Before this pass code (14px) and prose (15px Inter) were already close to parity by coincidence.
Finding 1 dropped prose to 12px without touching either code path, breaking that parity for the
first time. Fixed by setting both to `0.75rem` directly: `fontSize: '0.75rem'` added to the `'&'`
block in `codemirror-outis-mneme-theme.ts`, and `html.outis-mneme div[class*='language-'] {
font-size: 0.75rem; }` added to `outis-mneme-theme.css` for the streaming path. Verified live —
`.cm-content` and `.markdown-prose` both compute to `12px` now.

## Finding 6 — `rounded-full` and third-party toast corners (scope expansion, live request)

Live use also surfaced that `rounded-full` — deliberately left round by the original theme spec
("those are genuine circles: avatars, dots, icon buttons") — reads as inconsistent with the flat
aesthetic once you're looking at real pill-shaped buttons (Sign in, Check Again) next to it. Per
explicit direction, flattened everywhere, not just corner-radius elements: added
`html.outis-mneme .rounded-full { border-radius: 0; }` (144 component files use the class; wins on
specificity the same way every other override in this file does, so no `!important` needed — see
Finding 4's correction for why). This is a deliberate reversal of the original spec's stated
reasoning for that one utility, not a bug fix.

Toast notifications (`svelte-sonner`) needed a separate fix — they carry their own
package-level `--border-radius` custom property and two hardcoded radii (a 4px action button, a
50% circular close button), none of it routed through Tailwind's `--radius-*` scale, so the
flattening above never reached them. Added targeted overrides for `[data-sonner-toaster]`,
`[data-button]`, `[data-close-button]`, and `.sonner-loading-bar`.

One known residual gap: a single inline `border-radius: 50%` in a scoped `<style>` block
(`Message.svelte`'s swipe-reply icon) isn't reachable by a global class selector — low-traffic,
left for a follow-up rather than chased down.

## Finding 7 — Browser autofill ignores the theme entirely (found live, now fixed)

Reported live: the login page's email/username field shows a white background once the browser
recognizes it for autofill. The field's own markup (`src/routes/auth/+page.svelte`) is already
`bg-transparent` — correct, theme-following CSS. The white background is the browser itself:
Chrome and Safari apply autofill styling through an internal UA style that plain `background-color`
cannot override at any specificity, with or without `!important`, once a field is autofilled or
the browser recognizes a saved credential for it. `-webkit-text-fill-color` similarly overrides
`color` independently. No handling for this existed anywhere in the codebase before this pass —
not specific to this theme, every existing theme has had this same gap, just invisible against
`dark`'s already-similar tones.

The only reliable override is the standard box-shadow-inset technique: paint an opaque inset
shadow the size of the field (visually replacing the background, since browsers don't intercept
`box-shadow`), pair it with `-webkit-text-fill-color` for the text, and set a very long
`background-color` transition so Chrome's periodic re-assertion of its own styling doesn't flash
through:

```css
html.outis-mneme input:-webkit-autofill,
html.outis-mneme input:-webkit-autofill:hover,
html.outis-mneme input:-webkit-autofill:focus,
html.outis-mneme input:-webkit-autofill:active {
	box-shadow: 0 0 0 1000px var(--color-gray-950) inset !important;
	-webkit-text-fill-color: var(--color-gray-50) !important;
	caret-color: var(--color-gray-50);
	transition: background-color 5000s ease-in-out 0s;
}
```

Not verified with a live autofill screenshot in this pass — forcing Chrome's real autofill UI
through browser automation isn't reliable (it depends on the browser's own saved-credential
heuristics, not something a script can trigger), and testing it live would have required signing
out of the account already in use, which wasn't worth doing just to get a screenshot of a
well-established, standard CSS technique. Confirmed only that the rule is syntactically valid
(clean HMR reload, no PostCSS errors) and correctly scoped. Worth a manual look next time the
field actually gets autofilled.

## Finding 8 — Finding 3's fix broke the "invert" primary-button pattern (found live, now fixed)

Reported live with a screenshot: the "Create" button in the New Calendar modal
(`CreateCalendarModal.svelte`) rendered as a white box with barely-legible text. Two compounding
issues, not one:

**Regression from Finding 3.** That fix targeted both `text-white` and `dark:text-white`. But bare
`text-white` (no `dark:` prefix, 159 files) turned out to be mostly the *light-mode* half of a
distinct, widespread pattern: `bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black
dark:hover:bg-gray-100` — Open WebUI's "invert" primary-button convention (192 usages of
`dark:bg-white` across 92 files: Save, Create, Send, and other primary CTAs). It's meant to pop
white-on-black in light mode and invert to black-on-white in dark mode via `dark:text-black`.
Finding 3's rule, scoped under `html.outis-mneme` for every property it touches, carries more
specificity than Tailwind's `dark:` variant selector for `color` — so it beat `dark:text-black`
outright, forcing near-white text onto what should have been dark text on a white button.
Fixed by narrowing Finding 3 to `dark:text-white` only, which has no light-mode counterpart to
fight and was the actual, correctly-scoped target all along.

**The button itself wasn't theme-aligned either way.** Even with readable text restored, a pure
white/black button is still a stark, literal-color surface sitting in an otherwise near-black,
one-green-accent UI — not fixable by a text-color correction alone. Re-skinned the dark-mode half
of the pattern onto the accent scale instead of literal white/black:

```css
html.outis-mneme [class~='dark:bg-white'] { background-color: var(--color-blue-500); }
html.outis-mneme [class~='dark:hover:bg-gray-100'] { background-color: var(--color-blue-400); }
html.outis-mneme [class~='dark:text-black'],
html.outis-mneme [class~='dark:text-gray-900'] { color: var(--color-gray-950); }
```

`dark:hover:bg-gray-100` (70 usages) was checked for collateral matches before targeting it: 69 of
70 pair directly with `dark:bg-white` on the same element; the one exception
(`ConfirmDialog.svelte`) uses the same near-white-button family with `dark:bg-gray-100` as its base
rather than pure white, so redirecting its hover step the same way is still correct, not
collateral damage. Verified live: the Create button now renders as the theme's green accent with
dark, readable text (screenshot-confirmed after landing this fix).

## Finding 10 — Finding 1 fixed two prose classes; 0.9375rem was hardcoded ~20 more times

Reported live via screenshot: a tool-status "Explored ..." chip and the "Follow up" suggestions
both read visibly larger than the response text sitting between them. Root cause: `0.9375rem`
(15px, the pre-fix reading-area size) turns out to be hardcoded as a repeated Tailwind arbitrary
value (`text-[0.9375rem]`) across roughly twenty message-chrome spots that were never wrapped in
`.markdown-prose`/`.input-prose`, so Finding 1 never reached them — the "Explored ..." chip
(`ConsecutiveDetailsGroup.svelte`, `StatusHistory/StatusItem.svelte`, `ToolCallDisplay.svelte`,
`Collapsible.svelte`), the message author-name label (`Name.svelte`), the user's own message
display and edit textarea (`UserMessage.svelte`, `ResponseMessage.svelte`, `OutputEditView.svelte`),
and structured-output rendering. One rule catches all of them, since they share the identical
class token:

```css
html.outis-mneme [class~='text-[0.9375rem]'] {
	font-size: calc(0.9375rem * var(--outis-mneme-prose-scale));
}
```

`FollowUps.svelte` used a different literal (`text-sm`, 14px) — rather than give it its own scale,
its two occurrences were moved onto `text-[0.9375rem]` directly in the component, so there's one
convention for "message reading chrome text size," not two. Verified live: both compute to `12px`
now (tested via `getComputedStyle` on a synthetic element carrying the class, since the actual
elements require a live chat to render).

While in the same screenshot: the "Explored" checkmark icon uses Tailwind's `emerald` family
(`text-emerald-500/600/700`, `dark:text-emerald-400`), a separate color scale from `green`/`blue`
that this theme never touched — a third green hue sitting next to the theme's actual accent.
7 usages across 6 files (tool-call chips, terminal/automation connection status). Mapped to the
accent instead:

```css
html.outis-mneme [class~='text-emerald-500'],
html.outis-mneme [class~='text-emerald-600'],
html.outis-mneme [class~='text-emerald-700'],
html.outis-mneme [class~='dark:text-emerald-400'] {
	color: var(--color-blue-500);
}
```

`border-emerald-500` (`AlertRenderer.svelte`'s TIP-callout border) was deliberately left alone —
that component assigns a distinct hue per markdown alert type (note/tip/important/warning/caution)
on purpose, and only the text-color inconsistency was what showed up live. Verified live: a
synthetic element with `text-emerald-500` computes to `rgb(45, 255, 143)`, the accent.

## Priority

1. **Finding 1** (font size) — highest user-visible impact, lowest risk. **Implemented** in
   `src/outis-mneme-theme.css`.
2. **Finding 2** (accent cliff) — quantitatively the largest single defect found (a `0.306` `L`
   jump against a `~0.08` baseline). **Implemented** (600–900 re-derived; 500/950 anchors
   untouched, per the plan above). Verified live post-deploy; the new 600/700 read fine in
   practice.
3. **Finding 4** — investigated, no code change; the suspected gap doesn't exist (see correction
   above).
4. **Finding 5** (code-block font size) — found live after 1/2 landed, exactly the kind of
   follow-up this pass anticipated. **Implemented** in both `codemirror-outis-mneme-theme.ts` and
   `outis-mneme-theme.css`.
5. **Finding 6** (`rounded-full` / toast corners) — scope expansion per explicit live direction.
   **Implemented**.
6. **Finding 3** (competing white/mint/amber ceilings) — turned out to have a one-rule fix once
   framed as a class-token override rather than a 368-site manual audit. **Implemented**.
7. **Finding 7** (browser autofill) — found live from direct user feedback on the login page, a
   gap that predates this theme (every existing theme has it). **Implemented**, not live-verified
   (see Finding 7 for why).
8. **Finding 8** (invert-button regression + re-skin) — found live via screenshot right after
   Finding 3 shipped; the highest-severity item found this session, since it made a real primary
   action button unreadable. **Implemented and screenshot-verified live.**

## Acceptance

- Chat compose box and the rendered response above it read at the same size. ✅ (verified live:
  both compute to `12px`)
- `NoteEditor`, `CitationModal`, and a tool's `Valves` panel read at a size consistent with the
  main thread, not at their pre-theme Inter measurements. ✅
- No accent-scale step between `500` and `900` drops WCAG contrast below `4.5:1` in one jump from
  its neighbor the way `500→600` currently did. ✅ (`500→600` now `14.7:1→9.5:1`, `600→700` now
  `9.5:1→5.8:1`) — verified live: `getComputedStyle` on `html.outis-mneme` returns the new hexes.
- A code block and the prose paragraph next to it read at the same size. ✅ (Finding 5; verified
  live: `.cm-content` and `.markdown-prose` both compute to `12px`)
- `rounded-full` elements (avatars, buttons, status dots) and toast notifications are flat. ✅
  (Finding 6; verified live: avatar `border-radius` computes to `0px`)
- `dark:text-white` sites resolve through the theme's own scale, not a separate unthemed white —
  and bare `text-white` is left alone so it still yields correctly to `dark:text-black` where that
  pairing exists. ✅ (Finding 3, corrected by Finding 8)
- Browser-autofilled inputs (login page and elsewhere) pick up the theme instead of the browser's
  own white/UA styling. ✅ implemented, ⚠️ not live-verified (Finding 7 — needs a real autofill
  trigger, which wasn't worth signing out of the live account to force)
- The "invert" primary-button pattern (Create/Save/Send) reads as the theme's green accent with
  dark, legible text, not a stark white box. ✅ (Finding 8; screenshot-verified live)
- `dark`/`oled-dark`/`light`/`her`/`system` remain unmodified — this is a same-theme consistency
  pass, not a scope change. ✅ (only `outis-mneme-theme.css` and
  `codemirror-outis-mneme-theme.ts` touched, all CSS changes scoped to `html.outis-mneme`)

## Verification and deployment record

Verified live against a real backend (not just the computed math above): npm-installed under
Node 20 (repo requires `>=20`; the ambient Node was 18), ran `npm run dev`, and connected it to
the real Open WebUI backend container on `outis` (port `3001`, tunneled to local `8080` — port
`8080` on `outis` is a separate llama.cpp inference server, not this app). Confirmed via
`getComputedStyle` in the running app, not just visual inspection, for every item checked off
above.

Shipped as commit `3b0c5b1d9` on `theme/outis-mneme`
(https://github.com/ankurtrapasiya/open-webui), built by `.github/workflows/docker-outis-mneme.yaml`
into `ghcr.io/ankurtrapasiya/open-webui:outis-mneme-3b0c5b1` (pinned) /
`:outis-mneme` (moving).

First deploy attempt used a manual `docker stop/rm/run` on `outis`, matching the running
container's config by hand. It got silently reverted about 30 minutes later: `outis` runs this
stack from `/home/ankurtrapasiya/GithubProjects/outis-mneme/docker-compose.yml`
(`name: llama-server`, which is also why the network is `llama-server_default` and the volume is
`llama-server_open-webui-data`), and that file still pinned `open-webui`'s image to the old
`outis-mneme-ddc98bb` tag. A `docker compose up` — triggered by something checking disk usage
inside the container (`docker events` shows an `exec` for `du -sh` on the data dirs right before
the revert) — reconciled the running container back to what the compose file declared, undoing
the manual swap. Fixed properly the second time: edited the `image:` line in that compose file to
`outis-mneme-3b0c5b1` and ran `docker compose up -d open-webui`, so the pinned tag is now the
actual source of truth and won't get reverted by a future reconcile. That compose-file edit lives
only on `outis`, outside this repo's git history — not committed anywhere by this pass.
