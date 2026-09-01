// Outis-Light CodeMirror theme — the light counterpart to
// codemirror-outis-mneme-theme.ts.
//
// Light mode previously passed `[]` here, i.e. CodeMirror's stock light
// theme, which is a different colour system from anything else in the app.
// This gives the light theme the same treatment the dark one got.
//
// Syntax colors are the one place the theme's "one accent" rule doesn't
// apply: reading code depends on telling token *categories* apart at a
// glance, so each category gets its own hue.
//
// The dark theme puts its four hues on one OKLCH lightness plane. On paper
// that isn't quite enough — the eye is more sensitive to lightness
// differences against a light ground — so these four are equalised by
// *contrast* instead, at 7.01-7.03:1 on the block's background. A 0.02
// spread, tighter than the dark theme's 8.4-8.9:1, so no token flickers
// against its neighbours.
//
//   green  H152  #105f31  keywords, control flow
//   cyan   H215  #005b6c  functions, types, classes (the names you scan for)
//   violet H300  #5f4687  numbers, booleans, None (literal values)
//   amber  H78   #6f4c00  strings, regexps, escapes (the only warm hue)
//
// Off the ring: identifiers sit just above it as the reading baseline
// (8.19:1), and structure sits below.
//
// As in the dark theme, the accent green does NOT appear here. Its job is to
// mark interaction — caret, selection, focus, links — and nothing in a code
// block is interactive. It still owns the editor chrome below.
import { EditorView } from '@codemirror/view';
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { tags } from '@lezer/highlight';

const bg = '#eff5f2'; // --color-gray-50
const gutterBg = '#e4ede8'; // --color-gray-100
const text = '#3a4d43'; // identifiers, same weight as prose body
const muted = '#5f7368'; // operators, punctuation -- 4.6:1
const gutterFg = '#7c8f84'; // line numbers -- 3.1:1
const mutedLight = '#d7e3dd'; // --color-gray-200 -- borders only
const comment = '#677c71'; // 4.1:1 -- readable, still recedes
const accent = '#008350'; // --color-blue-500 -- editor chrome only, never syntax
const green = '#105f31';
const cyan = '#005b6c';
const violet = '#5f4687';
const amber = '#6f4c00';
const accentSoft = 'rgba(0, 131, 80, 0.14)'; // selection
const accentFaint = 'rgba(0, 131, 80, 0.05)'; // active line
const danger = '#b63032';

export const outisLightEditorTheme = /*@__PURE__*/ EditorView.theme(
	{
		// @codemirror/view's own baseTheme hardcodes .cm-editor { font-size: 14px },
		// unrelated to anything in this theme -- but the reading area is 12px
		// (OUTIS_MNEME_CONSISTENCY_SPEC.md Finding 1), so code would read visibly
		// larger than the text around it. Matches the same 12px so a code block
		// and the paragraph next to it read at the same size.
		'&': { color: text, backgroundColor: bg, fontSize: '0.75rem' },
		'.cm-content': { caretColor: accent },
		'.cm-cursor, .cm-dropCursor': { borderLeftColor: accent },
		'&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection':
			{ backgroundColor: accentSoft },
		'.cm-panels': { backgroundColor: gutterBg, color: text },
		'.cm-panels.cm-panels-top': { borderBottom: `2px solid ${mutedLight}` },
		'.cm-panels.cm-panels-bottom': { borderTop: `2px solid ${mutedLight}` },
		'.cm-searchMatch': { backgroundColor: accentSoft, outline: `1px solid ${accent}` },
		'.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: accentSoft },
		'.cm-activeLine': { backgroundColor: accentFaint },
		'.cm-selectionMatch': { backgroundColor: accentFaint },
		'&.cm-focused .cm-matchingBracket, &.cm-focused .cm-nonmatchingBracket': {
			backgroundColor: accentSoft
		},
		'.cm-gutters': { backgroundColor: bg, color: gutterFg, border: 'none' },
		'.cm-activeLineGutter': { backgroundColor: accentFaint, color: text },
		'.cm-foldPlaceholder': { backgroundColor: 'transparent', border: 'none', color: muted },
		'.cm-tooltip': { border: `1px solid ${mutedLight}`, backgroundColor: gutterBg },
		'.cm-tooltip .cm-tooltip-arrow:before': {
			borderTopColor: 'transparent',
			borderBottomColor: 'transparent'
		},
		'.cm-tooltip .cm-tooltip-arrow:after': {
			borderTopColor: gutterBg,
			borderBottomColor: gutterBg
		},
		'.cm-tooltip-autocomplete': {
			'& > ul > li[aria-selected]': { backgroundColor: accentFaint, color: text }
		}
	},
	{ dark: false }
);

const outisLightHighlightStyle = /*@__PURE__*/ HighlightStyle.define([
	// Keywords and control flow.
	// (control/operator/definition/module keywords are all subtypes of
	// tags.keyword, so the one rule covers `def`, `if`, `in`, `import`.)
	{ tag: [tags.keyword, tags.modifier], color: green },

	// Names you scan for: what's being defined and what's being called.
	// Exact tags, not just the base ones — lezer-python emits
	// function(definition(variableName)) for a `def` name, and matching it
	// exactly keeps it from falling through to the plain-identifier rule.
	{
		tag: [
			tags.function(tags.variableName),
			tags.function(tags.definition(tags.variableName)),
			tags.function(tags.propertyName),
			tags.labelName,
			tags.macroName
		],
		color: cyan
	},
	{
		tag: [
			tags.typeName,
			tags.className,
			tags.definition(tags.className),
			tags.namespace,
			tags.annotation
		],
		color: cyan
	},

	// Literal values.
	{
		tag: [
			tags.number,
			tags.integer,
			tags.float,
			tags.bool,
			tags.atom,
			tags.null,
			tags.unit,
			tags.constant(tags.name),
			tags.standard(tags.name),
			tags.self,
			tags.special(tags.variableName),
			tags.color
		],
		color: violet
	},

	// Text data — the only warm hue in the block.
	{
		tag: [
			tags.string,
			tags.character,
			tags.special(tags.string),
			tags.regexp,
			tags.escape,
			tags.processingInstruction,
			tags.inserted
		],
		color: amber
	},

	// Plain identifiers, properties, definitions.
	{
		tag: [
			tags.name,
			tags.variableName,
			tags.definition(tags.variableName),
			tags.propertyName,
			tags.attributeName
		],
		color: text
	},

	// Structure — present but never competing with the tokens above.
	{
		tag: [
			tags.operator,
			tags.punctuation,
			tags.separator,
			tags.bracket,
			tags.derefOperator,
			tags.meta
		],
		color: muted
	},
	{ tag: tags.comment, color: comment, fontStyle: 'italic' },

	// Markup.
	{ tag: tags.strong, fontWeight: 'bold' },
	{ tag: tags.emphasis, fontStyle: 'italic' },
	{ tag: tags.strikethrough, textDecoration: 'line-through' },
	{ tag: [tags.link, tags.url], color: cyan, textDecoration: 'underline' },
	{ tag: tags.heading, fontWeight: 'bold', color: text },
	{ tag: [tags.deleted, tags.changed], color: danger },
	{ tag: tags.invalid, color: danger, textDecoration: 'underline wavy' }
]);

export const outisLight = [outisLightEditorTheme, syntaxHighlighting(outisLightHighlightStyle)];
