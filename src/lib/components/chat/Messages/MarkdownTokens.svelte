<script lang="ts">
	import { marked } from 'marked';
	import type { Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import { onMount } from 'svelte';
	import MarkdownInlineTokens from '$lib/components/chat/Messages/MarkdownInlineTokens.svelte';

	export let id: string;
	export let tokens: Token[];
	export let top = true;

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};

	const renderer = new marked.Renderer();
	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code class="codespan">${code.replaceAll('&amp;', '&')}</code>`;
	};

	renderer.code = (code, lang) => {
		return `<pre><code class="language-${lang}">${code}</code></pre>`;
	};

	// Open all links in a new tab/window (from https://github.com/markedjs/marked/issues/655#issuecomment-383226346)
	const origLinkRenderer = renderer.link;
	renderer.link = (href, title, text) => {
		const html = origLinkRenderer.call(renderer, href, title, text);
		return html.replace(/^<a /, '<a target="_blank" rel="nofollow" ');
	};
	const { extensions, ...defaults } = marked.getDefaults() as marked.MarkedOptions & {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		extensions: any;
	};
</script>

{#each tokens as token, tokenIdx (`${id}-${tokenIdx}`)}
	{#if token.type === 'code'}
		{#if token.lang === 'mermaid'}
			<pre class="mermaid">{revertSanitizedResponseContent(token.text)}</pre>
		{:else}
			<CodeBlock
				id={`${id}-${tokenIdx}`}
				lang={token?.lang ?? ''}
				code={revertSanitizedResponseContent(token?.text ?? '')}
			/>
		{/if}
		<!-- {:else if token.type === 'heading'}
		<svelte:element this={headerComponent(token.depth)}>
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-h`} tokens={token.tokens} />
		</svelte:element>
	{:else if token.type === 'hr'}
		<hr />
	{:else if token.type === 'blockquote'}
		<blockquote>
			<svelte:self id={`${id}-${tokenIdx}`} tokens={token.tokens} />
		</blockquote>
	{:else if token.type === 'html'}
		{@html token.text}
	{:else if token.type === 'paragraph'}
		<p>
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-p`} tokens={token.tokens ?? []} />
		</p>
	{:else if token.type === 'list'}
		{#if token.ordered}
			<ol start={token.start || 1}>
				{#each token.items as item, itemIdx}
					<li>
						<svelte:self
							id={`${id}-${tokenIdx}-${itemIdx}`}
							tokens={item.tokens}
							top={token.loose}
						/>
					</li>
				{/each}
			</ol>
		{:else}
			<ul>
				{#each token.items as item, itemIdx}
					<li>
						<svelte:self
							id={`${id}-${tokenIdx}-${itemIdx}`}
							tokens={item.tokens}
							top={token.loose}
						/>
					</li>
				{/each}
			</ul>
		{/if}
	{:else if token.type === 'table'}
		<table>
			<thead>
				<tr>
					{#each token.header as header, headerIdx}
						<th style={token.align[headerIdx] ? '' : `text-align: ${token.align[headerIdx]}`}>
							<MarkdownInlineTokens
								id={`${id}-${tokenIdx}-header-${headerIdx}`}
								tokens={header.tokens}
							/>
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each token.rows as row, rowIdx}
					<tr>
						{#each row ?? [] as cell, cellIdx}
							<td style={token.align[cellIdx] ? '' : `text-align: ${token.align[cellIdx]}`}>
								<MarkdownInlineTokens
									id={`${id}-${tokenIdx}-row-${rowIdx}-${cellIdx}`}
									tokens={cell.tokens}
								/>
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	{:else if token.type === 'text'} -->
		<!-- {#if top}
			<p>
				{#if token.tokens}
					<MarkdownInlineTokens id={`${id}-${tokenIdx}-t`} tokens={token.tokens} />
				{:else}
					{unescapeHtml(token.text)}
				{/if}
			</p>
		{:else if token.tokens}
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-p`} tokens={token.tokens ?? []} />
		{:else}
			{unescapeHtml(token.text)}
		{/if} -->
	{:else}
		{@html marked.parse(token.raw, {
			...defaults,
			gfm: true,
			breaks: true,
			renderer
		})}
	{/if}
{/each}
