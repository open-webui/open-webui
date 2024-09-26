<script lang="ts">
	import DOMPurify from 'dompurify';
	import { onMount } from 'svelte';
	import { marked, type Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';

	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import MarkdownInlineTokens from '$lib/components/chat/Messages/Markdown/MarkdownInlineTokens.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let id: string;
	export let tokens: Token[];
	export let top = true;

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};
</script>

<!-- {JSON.stringify(tokens)} -->
{#each tokens as token, tokenIdx (tokenIdx)}
	{#if token.type === 'hr'}
		<hr />
	{:else if token.type === 'heading'}
		<svelte:element this={headerComponent(token.depth)}>
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-h`} tokens={token.tokens} />
		</svelte:element>
	{:else if token.type === 'code'}
		<CodeBlock
			id={`${id}-${tokenIdx}`}
			{token}
			lang={token?.lang ?? ''}
			code={revertSanitizedResponseContent(token?.text ?? '')}
		/>
	{:else if token.type === 'table'}
		<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
			<table class="w-full">
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
		</div>
	{:else if token.type === 'blockquote'}
		<blockquote>
			<svelte:self id={`${id}-${tokenIdx}`} tokens={token.tokens} />
		</blockquote>
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
	{:else if token.type === 'html'}
		{@const html = DOMPurify.sanitize(token.text)}
		{#if html && html.includes('<video')}
			{@html html}
		{:else if token.text.includes(`<iframe src="${WEBUI_BASE_URL}/api/v1/files/`)}
			{@html `${token.text}`}
		{:else}
			{token.text}
		{/if}
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
		></iframe>
	{:else if token.type === 'paragraph'}
		<p>
			<MarkdownInlineTokens id={`${id}-${tokenIdx}-p`} tokens={token.tokens ?? []} />
		</p>
	{:else if token.type === 'text'}
		{#if top}
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
		{/if}
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer
				content={revertSanitizedResponseContent(token.text)}
				displayMode={token?.displayMode ?? false}
			/>
		{/if}
	{:else if token.type === 'blockKatex'}
		{#if token.text}
			<KatexRenderer
				content={revertSanitizedResponseContent(token.text)}
				displayMode={token?.displayMode ?? false}
			/>
		{/if}
	{:else if token.type === 'space'}
		<div class="my-2" />
	{:else}
		{console.log('Unknown token', token)}
	{/if}
{/each}
