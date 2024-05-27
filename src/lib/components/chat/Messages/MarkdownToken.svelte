<script lang="ts">
	import type { Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import MarkdownInlineToken from '$lib/components/chat/Messages/MarkdownInlineTokens.svelte';
	import { onMount } from 'svelte';
	import MarkdownInlineTokens from '$lib/components/chat/Messages/MarkdownInlineTokens.svelte';

	export let id: string;
	export let token: Token;
	export let top = true;

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};

	onMount(() => {
		console.log('MarkdownToken', id, token, top);
	});
</script>

{#if token.type === 'hr'}
	<hr />
{:else if token.type === 'heading'}
	<svelte:element this={headerComponent(token.depth)}>
		<MarkdownInlineTokens id={`${id}-h`} tokens={token.tokens} />
	</svelte:element>
{:else if token.type === 'code'}
	<CodeBlock
		{id}
		lang={token?.lang ?? ''}
		code={revertSanitizedResponseContent(token?.text ?? '')}
	/>
{:else if token.type === 'table'}
	<table>
		<thead>
			<tr>
				{#each token.header as header, headerIdx}
					<th style={token.align[headerIdx] ? '' : `text-align: ${token.align[headerIdx]}`}>
						<MarkdownInlineTokens id={`${id}-header-${headerIdx}`} tokens={header.tokens} />
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each token.rows as row, rowIdx}
				<tr>
					{#each row ?? [] as cell, cellIdx}
						<td style={token.align[cellIdx] ? '' : `text-align: ${token.align[cellIdx]}`}>
							<MarkdownInlineTokens id={`${id}-row-${rowIdx}-${cellIdx}`} tokens={cell.tokens} />
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
{:else if token.type === 'blockquote'}
	<blockquote>
		{#each token.tokens ?? [] as innerToken, tokenIdx}
			<svelte:self id={`${id}-${tokenIdx}`} token={innerToken} />
		{/each}
	</blockquote>
{:else if token.type === 'list'}
	{#if token.ordered}
		<ol start={token.start || 1}>
			{#each token.items as item, itemIdx}
				<li>
					{#each item.tokens ?? [] as innerToken, tokenIdx}
						<svelte:self id={`${id}-${itemIdx}-${tokenIdx}`} token={innerToken} top={token.loose} />
					{/each}
				</li>
			{/each}
		</ol>
	{:else}
		<ul>
			{#each token.items as item, itemIdx}
				<li>
					{#each item.tokens ?? [] as innerToken, tokenIdx}
						<svelte:self id={`${id}-${itemIdx}-${tokenIdx}`} token={innerToken} top={token.loose} />
					{/each}
				</li>
			{/each}
		</ul>
	{/if}
{:else if token.type === 'html'}
	{@html token.text}
{:else if token.type === 'paragraph'}
	<p>
		<MarkdownInlineTokens id={`${id}-p`} tokens={token.tokens ?? []} />
	</p>
{:else if token.type === 'text'}
	{#if top}
		<p>
			{#if token.tokens}
				<MarkdownInlineTokens id={`${id}-t`} tokens={token.tokens} />
			{:else}
				{unescapeHtml(token.text)}
			{/if}
		</p>
	{:else if token.tokens}
		<MarkdownInlineTokens id={`${id}-p`} tokens={token.tokens ?? []} />
	{:else}
		{unescapeHtml(token.text)}
	{/if}
{:else if token.type === 'space'}
	{''}
{:else}
	{console.log('Unknown token', token)}
{/if}
