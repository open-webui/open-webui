<script lang="ts">
	import DOMPurify from 'dompurify';
	import type { Token } from 'marked';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import Source from './Source.svelte';

	export let id: string;
	export let token: Token;

	export let onSourceClick: Function = () => {};

	let html: string | null = null;

	$: if (token.type === 'html' && token?.text) {
		html = DOMPurify.sanitize(token.text);
	} else {
		html = null;
	}
</script>

{#if token.type === 'html'}
	{#if html && html.includes('<video')}
		{@html html}
	{:else if token.text && token.text.match(/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/)}
		{@const match = token.text.match(
			/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/
		)}
		{@const ytId = match && match[1]}
		{#if ytId}
			<iframe
				class="w-full aspect-video my-2"
				src={`https://www.youtube.com/embed/${ytId}`}
				title="YouTube video player"
				frameborder="0"
				allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
			>
			</iframe>
		{/if}
	{:else if token.text.includes(`<iframe src="${WEBUI_BASE_URL}/api/v1/files/`)}
		{@html `${token.text}`}
	{:else if token.text.includes(`<source_id`)}
		<Source {id} {token} onClick={onSourceClick} />
	{:else}
		{token.text}
	{/if}
{/if}
