<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';

	export let className = ' w-full outline-hidden z-10';
	export let imageClassName = 'rounded-lg mx-auto scale-85 hover:scale-115 shadow-[0_-4px_10px_rgba(0,0,0,0.5)] hover:shadow-[0_-6px_15px_rgba(0,0,0,0.6)]';

	let _src = '';
	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;

	let _caption = '';
	$: _caption = alt;

	let showImagePreview = false;
</script>

<button
	class={`text-center ${className}`}
	on:click={() => {
		showImagePreview = false;
	}}
	type="button"
>
	<img src={_src} {alt} class={imageClassName} draggable="false" data-cy="image" />
	{@html _caption}
</button>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} />
