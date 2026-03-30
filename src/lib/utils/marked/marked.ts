/**
 * Markdown parsing (Marked instance, lexer, HTML render). No DOMPurify — safe for Web Worker bundles
 * that import only from this module.
 *
 * UI code may import from `$lib/utils/marked` (index) for `renderMarkdownToHTMLSanitized`.
 *
 * Do not import "marked" elsewhere or call marked.use().
 */

import { Marked, type TokensList, type MarkedOptions } from 'marked';
import markedExtension from './extension';
import markedKatexExtension from './katex-extension';
import { disableSingleTildeExtension } from './strikethrough-extension';
import { mentionExtension } from './mention-extension';
import footnoteExtensionDefault from './footnote-extension';
import citationExtensionDefault from './citation-extension';
import colonFenceExtension from './colon-fence-extension';

/** Shared base options (no callbacks that close over component context). */
const baseOptions = {
	throwOnError: false,
	breaks: true,
	gfm: true
};

/** Task list renderer: outputs data-type="taskList" / "taskItem" for the UI; no component context. */
const taskListRenderer = {
	list(body: string, ordered: boolean, start: number | ''): string {
		const isTaskList = body.includes('data-checked=');
		if (isTaskList) {
			return `<ul data-type="taskList">${body}</ul>`;
		}
		const type = ordered ? 'ol' : 'ul';
		const startAttr = ordered && start !== 1 ? ` start="${start}"` : '';
		return `<${type}${startAttr}>${body}</${type}>`;
	},
	listitem(text: string, task: boolean, checked: boolean): string {
		if (task) {
			const checkedAttr = checked ? 'true' : 'false';
			return `<li data-type="taskItem" data-checked="${checkedAttr}">${text}</li>`;
		}
		return `<li>${text}</li>`;
	}
};

/**
 * Single marked instance used by the app. Configured once at load; holds no Svelte context.
 */
const markedInstance = new Marked(
	markedKatexExtension(baseOptions),
	markedExtension(baseOptions),
	citationExtensionDefault(),
	footnoteExtensionDefault(),
	colonFenceExtension(baseOptions),
	disableSingleTildeExtension(),
	{
		extensions: [
			mentionExtension({ triggerChar: '@' }),
			mentionExtension({ triggerChar: '#' }),
			mentionExtension({ triggerChar: '$' })
		]
	},
	{
		...baseOptions,
		renderer: taskListRenderer
	}
);

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type { Token, TokensList } from 'marked';

/**
 * Options for renderMarkdownToHTML(). Only pass options that do not hold component references.
 */
export interface MarkedParseOptions {
	/** Whether to parse asynchronously (default false). */
	async?: boolean;
	/** Optional highlighter for code blocks; must not close over component/store. */
	highlight?: (code: string, lang: string) => string;
	[key: string]: unknown;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

/**
 * Lex Markdown into a token list (no HTML rendering). Use for token-based rendering (e.g. chat messages).
 *
 * @param markdown - Raw markdown (can be preprocessed with replaceTokens / processResponseContent)
 * @param options - Optional; usually omitted
 * @returns Token list (with links etc.)
 */
export function lexer(markdown: string, options?: MarkedOptions | null): TokensList {
	return markedInstance.lexer(markdown, options ?? undefined);
}

/**
 * Render Markdown to HTML.
 *
 * @param markdown - Raw markdown text
 * @param options - Optional render options (e.g. async, highlight). Do not pass renderer/walkTokens etc.
 * @returns HTML string (sync) or Promise<string> (when async: true)
 */
export function renderMarkdownToHTML(
	markdown: string,
	options?: MarkedParseOptions | null
): string | Promise<string> {
	return markedInstance.parse(markdown, options as MarkedOptions) as string | Promise<string>;
}
