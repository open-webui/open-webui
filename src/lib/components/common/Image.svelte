<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { t } from 'i18next';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';
	export let isMarkdown: boolean = true;
	export let showImagePreview = false;

	export let className = ' w-full';

	let _src = '';
	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;

	function openImagePreview() {
		showImagePreview = true;
		console.log(isMarkdown);
	}
</script>

<button class={className} on:click={openImagePreview}>
	<img src={_src} {alt} class="rounded-lg cursor-pointer" draggable="false" data-cy="image" />
</button>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} {isMarkdown} />
