<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';

	let _src = '';

	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;

	let showImagePreview = false;
</script>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} />
<button
	on:click={() => {
		console.log('image preview');
		showImagePreview = true;
	}}
>
	<img src={_src} {alt} class=" max-h-96 rounded-lg" draggable="false" />
</button>
