<script lang="ts">
	import type { Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import { onMount } from 'svelte';
	import InlineEscape from '$lib/components/chat/Messages/Markdown/InlineEscape.svelte';
	import InlineHtml from '$lib/components/chat/Messages/Markdown/InlineHtml.svelte';
	import InlineLink from '$lib/components/chat/Messages/Markdown/InlineLink.svelte';

	export let id: string;
	export let token: Token;

	onMount(() => {
		console.log('MarkdownInlineToken', id, token, top);
	});
</script>

{#if token.type === 'escape'}
	<InlineEscape {token} />
{:else if token.type === 'html'}
	<InlineHtml {token} />
{:else if token.type === 'link'}
	<InlineLink {token} />
{:else if token.type === 'image'}
	<img src={token.href} alt={token.text} title={token.title} />
{:else if token.type === 'strong'}
	<strong>
		{#each token.tokens ?? [] as innerToken, tokenIdx}
			<svelte:self id={`${id}-${tokenIdx}`} token={innerToken} />
		{/each}
	</strong>
{:else if token.type === 'em'}
	<em>
		{#each token.tokens ?? [] as innerToken, tokenIdx}
			<svelte:self id={`${id}-${tokenIdx}`} token={innerToken} />
		{/each}
	</em>
{:else if token.type === 'codespan'}
	<code>{unescapeHtml(token.text)}</code>
{:else if token.type === 'br'}
	<br />
{:else if token.type === 'del'}
	<del>
		{#each token.tokens ?? [] as innerToken, tokenIdx}
			<svelte:self id={`${id}-${tokenIdx}`} token={innerToken} />
		{/each}
	</del>
{:else if token.type === 'text'}
	{unescapeHtml(token.text)}
{/if}
