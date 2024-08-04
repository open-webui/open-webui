<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';
	export let isMarkdown = false;
	export let showImagePreview = false;

	let _src = '';

	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;
</script>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} {isMarkdown} />
<button
	on:click={() => {
		console.log('image preview');
		showImagePreview = true;
	}}
>
	<img
		src={_src}
		{alt}
		class={isMarkdown ? 'w-full hljs' : 'max-h-96 rounded-lg'}
		draggable="false"
		data-cy="image"
	/>
</button>
