<script lang="ts">
	import type { Token } from 'marked';
	import { unescapeHtml } from '$lib/utils';
	import Image from '$lib/components/common/Image.svelte';

	export let id: string;
	export let tokens: Token[];
</script>

{#each tokens as token}
	{#if token.type === 'escape'}
		{unescapeHtml(token.text)}
	{:else if token.type === 'html'}
		{@html token.text}
	{:else if token.type === 'link'}
		<a href={token.href} target="_blank" rel="nofollow" title={token.title}>{token.text}</a>
	{:else if token.type === 'image'}
		<Image src={token.href} alt={token.text} />
	{:else if token.type === 'strong'}
		<strong>
			<svelte:self id={`${id}-strong`} tokens={token.tokens} />
		</strong>
	{:else if token.type === 'em'}
		<em>
			<svelte:self id={`${id}-em`} tokens={token.tokens} />
		</em>
	{:else if token.type === 'codespan'}
		<code class="codespan">{unescapeHtml(token.text.replaceAll('&amp;', '&'))}</code>
	{:else if token.type === 'br'}
		<br />
	{:else if token.type === 'del'}
		<del>
			<svelte:self id={`${id}-del`} tokens={token.tokens} />
		</del>
	{:else if token.type === 'text'}
		{unescapeHtml(token.text)}
	{/if}
{/each}
