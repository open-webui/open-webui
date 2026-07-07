import { marked } from 'marked';
import hljs from 'highlight.js';

import markedExtension from '$lib/utils/marked/extension';
import markedKatexExtension from '$lib/utils/marked/katex-extension';

const MARKDOWN_CLIPBOARD_TYPE = 'text/markdown';

type SupportsClipboardType = (mimeType: string) => boolean;

const supportsClipboardType: SupportsClipboardType = (mimeType) => {
	const clipboardItem = globalThis.ClipboardItem as
		| (typeof ClipboardItem & { supports?: SupportsClipboardType })
		| undefined;

	return Boolean(clipboardItem?.supports?.(mimeType));
};

const createFormattedHtml = (text: string) => {
	const options = {
		throwOnError: false,
		highlight: function (code: string, lang: string) {
			const language = hljs.getLanguage(lang) ? lang : 'plaintext';
			return hljs.highlight(code, { language }).value;
		}
	};
	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));
	// DEVELOPER NOTE: Go to `$lib/components/chat/Messages/Markdown.svelte` to add extra markdown extensions for rendering.

	const htmlContent = marked.parse(text, { async: false }) as string;

	// Add basic styling to make the content look better when pasted.
	return `
			<div>
				<style>
					pre {
						background-color: #f6f8fa;
						border-radius: 6px;
						padding: 16px;
						overflow: auto;
					}
					code {
						font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
						font-size: 14px;
					}
					.hljs-keyword { color: #d73a49; }
					.hljs-string { color: #032f62; }
					.hljs-comment { color: #6a737d; }
					.hljs-function { color: #6f42c1; }
					.hljs-number { color: #005cc5; }
					.hljs-operator { color: #d73a49; }
					.hljs-class { color: #6f42c1; }
					.hljs-title { color: #6f42c1; }
					.hljs-params { color: #24292e; }
					.hljs-built_in { color: #005cc5; }
					blockquote {
						border-left: 4px solid #dfe2e5;
						padding-left: 16px;
						color: #6a737d;
						margin-left: 0;
						margin-right: 0;
					}
					table {
						border-collapse: collapse;
						width: 100%;
						margin-bottom: 16px;
					}
					table, th, td {
						border: 1px solid #dfe2e5;
					}
					th, td {
						padding: 8px 12px;
					}
					th {
						background-color: #f6f8fa;
					}
				</style>
				${htmlContent}
			</div>
		`;
};

export const createFormattedClipboardItemData = (
	text: string,
	html: string | null = null,
	supportsType: SupportsClipboardType = supportsClipboardType
) => {
	const data: Record<string, Blob> = {
		'text/plain': new Blob([text], { type: 'text/plain' })
	};

	if (supportsType(MARKDOWN_CLIPBOARD_TYPE)) {
		data[MARKDOWN_CLIPBOARD_TYPE] = new Blob([text], { type: MARKDOWN_CLIPBOARD_TYPE });
	}

	data['text/html'] = new Blob([html ?? createFormattedHtml(text)], { type: 'text/html' });

	return data;
};
