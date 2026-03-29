/**
 * Centralized Markdown utilities: re-exports parse API from `./marked` and adds DOMPurify sanitize.
 *
 * Worker-friendly imports: use `$lib/utils/marked/marked` (lexer / renderMarkdownToHTML only).
 */

import DOMPurify from 'dompurify';
import { renderMarkdownToHTML, type MarkedParseOptions } from './marked';

export type { Token, TokensList, MarkedParseOptions } from './marked';
export { lexer, renderMarkdownToHTML } from './marked';

/**
 * Render Markdown to HTML and sanitize with DOMPurify. Use when rendering arbitrary markdown into the DOM
 * (banners, footers, toasts, confirm dialogs, etc.) so callers do not need to call DOMPurify separately.
 *
 * @param markdown - Raw markdown text
 * @param options - Optional render options (e.g. highlight). Do not pass callbacks that capture component context.
 * @returns Sanitized HTML string (sync only; for async use renderMarkdownToHTML() then DOMPurify.sanitize yourself)
 */
export function renderMarkdownToHTMLSanitized(
	markdown: string,
	options?: MarkedParseOptions | null
): string {
	const raw = renderMarkdownToHTML(markdown, options);
	const html = typeof raw === 'string' ? raw : '';
	return DOMPurify.sanitize(html);
}
