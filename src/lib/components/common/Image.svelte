<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';
	import { showSidebar } from '$lib/stores';

	export let src = '';
	export let alt = '';
	export let showImagePreview = false;

	let _src = '';
	let isShowSidebar = $showSidebar;

	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;
</script>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} {isShowSidebar} />
<button
	on:click={() => {
		console.log('image preview');
		showImagePreview = true;
		showSidebar.set(false);
	}}
>
	<img src={_src} {alt} class=" max-h-96 rounded-lg" draggable="false" data-cy="image" />
</button>
