<script lang="ts">
	import DOMPurify from 'dompurify';
	import type { Token } from 'marked';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import Source from './Source.svelte';
	import { settings } from '$lib/stores';

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
		{@const video = html.match(/<video[^>]*>([\s\S]*?)<\/video>/)}
		{@const videoSrc = video && video[1]}
		{#if videoSrc}
			<!-- svelte-ignore a11y-media-has-caption -->
			<video
				class="w-full my-2"
				src={videoSrc}
				title="Video player"
				frameborder="0"
				referrerpolicy="strict-origin-when-cross-origin"
				controls
				allowfullscreen
			></video>
		{:else}
			{token.text}
		{/if}
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
	{:else if token.text.includes(`<file type="html"`)}
		{@const match = token.text.match(/<file type="html" id="([^"]+)"/)}
		{@const fileId = match && match[1]}
		{#if fileId}
			<iframe
				class="w-full my-2"
				src={`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content/html`}
				title="Content"
				frameborder="0"
				sandbox="allow-scripts{($settings?.iframeSandboxAllowForms ?? false)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
				width="100%"
				onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
			></iframe>
		{/if}
	{:else if token.text.includes(`<source_id`)}
		<Source {id} {token} onClick={onSourceClick} />
	{:else}
		{token.text}
	{/if}
{/if}
