/**
 * Centralized Markdown utilities: re-exports parse API from `./marked` and adds DOMPurify sanitize.
 *
 * Worker-friendly imports: use `$lib/utils/marked/marked` (lexer / renderMarkdownToHTML only).
 */

import DOMPurify, { type Config as DOMPurifyConfig } from 'dompurify';
import { renderMarkdownToHTML, type MarkedParseOptions } from './marked';

export type { Token, TokensList, MarkedParseOptions } from './marked';
export { lexer, renderMarkdownToHTML } from './marked';

export interface RenderMarkdownToHTMLSanitizedOptions {
	markedOptions?: MarkedParseOptions | null;
	sanitizeOptions?: DOMPurifyConfig | null;
}

/**
 * Render Markdown to HTML and sanitize with DOMPurify. Use when rendering arbitrary markdown into the DOM
 * (banners, footers, toasts, confirm dialogs, etc.) so callers do not need to call DOMPurify separately.
 *
 * @param markdown - Raw markdown text
 * @param options - Optional markdown parse and sanitize options.
 * @returns Sanitized HTML string (sync only; for async use renderMarkdownToHTML() then DOMPurify.sanitize yourself)
 */
export function renderMarkdownToHTMLSanitized(
	markdown: string,
	options?: RenderMarkdownToHTMLSanitizedOptions | null
): string {
	const html = renderMarkdownToHTML(markdown, options?.markedOptions);
	return DOMPurify.sanitize(html, options?.sanitizeOptions ?? undefined);
}
