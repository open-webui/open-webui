<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';
	export let isMarkdown = false;
	export let showImagePreview = false;

	export let className = '';

	let _src = '';
	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;
</script>

<button
	class={className}
	on:click={() => {
		showImagePreview = true;
	}}
>
	<img src={_src} {alt} class=" rounded-lg cursor-pointer" draggable="false" data-cy="image" />
</button>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} {isMarkdown} />
