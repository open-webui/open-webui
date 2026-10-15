<script lang="ts" context="module">
	import { Marked } from 'marked';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { footnoteExtension } from '$lib/utils/marked/footnote-extension';

	// Documents must not inherit chat's global extensions or soft-line-break settings.
	const documentMarkdown = new Marked(markedKatexExtension(), {
		breaks: false,
		extensions: [
			{
				...footnoteExtension(),
				renderer: (token) => `<sup class="footnote-ref">${token.escapedText}</sup>`
			}
		]
	});
</script>

<script lang="ts">
	import { setContext } from 'svelte';
	import MarkdownTokens from '../Messages/Markdown/MarkdownTokens.svelte';
	import type { Token } from 'marked';

	export let content: string;
	export let id: string;

	setContext('markdown', {
		document: true,
		allowRemoteContent: true,
		lexer: (source: string) => documentMarkdown.lexer(source),
		parseInline: (tokens: Token[]) =>
			documentMarkdown.Parser.parseInline(tokens, documentMarkdown.defaults)
	});
	$: tokens = documentMarkdown.lexer(content);
</script>

<div class="document-markdown prose prose-sm dark:prose-invert min-w-0 max-w-none p-3">
	<MarkdownTokens {id} {tokens} editCodeBlock={false} />
</div>

<style>
	.document-markdown {
		font-size: 0.75rem;
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	.document-markdown :global(h1),
	.document-markdown :global(h2),
	.document-markdown :global(h3),
	.document-markdown :global(h4),
	.document-markdown :global(h5),
	.document-markdown :global(h6) {
		margin: 1rem 0 0.375rem;
		font-weight: 600;
		line-height: 1.3;
	}
	.document-markdown :global(h1) {
		font-size: 1.125rem;
	}
	.document-markdown :global(h2) {
		font-size: 1rem;
	}
	.document-markdown :global(h3) {
		font-size: 0.875rem;
	}
	.document-markdown :global(h4),
	.document-markdown :global(h5),
	.document-markdown :global(h6) {
		font-size: 0.75rem;
	}
	.document-markdown :global(p),
	.document-markdown :global(ul),
	.document-markdown :global(ol) {
		margin: 0.5rem 0;
	}
	.document-markdown :global(li) {
		margin: 0.125rem 0;
	}
	.document-markdown :global(blockquote) {
		margin: 0.75rem 0;
		font-style: normal;
		font-weight: 400;
	}
	.document-markdown :global(strong) {
		font-weight: 600;
	}
	.document-markdown :global(hr) {
		margin: 0.75rem 0;
	}
	.document-markdown :global(img) {
		margin: 0.5rem 0;
	}
	.document-markdown :global(table) {
		font-size: 0.75rem;
		margin: 0.5rem 0;
	}
	.document-markdown :global(th),
	.document-markdown :global(td) {
		padding: 0.375rem 0.5rem !important;
	}
	.document-markdown :global(pre) {
		margin: 0.5rem 0;
		font-family: var(--font-mono);
	}
	.document-markdown :global(pre.hljs) {
		padding: 0.5rem 0.75rem;
	}
	.document-markdown :global(pre code) {
		font-size: 0.75rem;
	}
	.document-markdown :global(.codespan) {
		font-size: 0.95em;
	}
	.document-markdown :global(input[type='checkbox']) {
		cursor: default;
	}
	.document-markdown :global(.document-code-block) {
		border-radius: 0.5rem;
	}
	.document-markdown :global(.document-code-block > .sticky) {
		padding: 0.25rem 0.5rem;
	}
	.document-markdown :global(.document-code-block > .sticky button) {
		height: 1.5rem;
		padding-inline: 0.375rem;
		font-size: 0.6875rem;
	}
	.document-markdown > :global(:first-child) {
		margin-top: 0;
	}
	.document-markdown > :global(:last-child) {
		margin-bottom: 0;
	}
</style>
