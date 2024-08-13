<script lang="ts">
	import katex from 'katex';
	import 'katex/contrib/mhchem';
	import 'katex/dist/katex.min.css';
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderedContent: HTMLElement;

	onMount(() => {
		if (renderedContent) {
			katex.render(content, renderedContent, {
				displayMode,
				throwOnError: false
			});
		}
	});
</script>

<div bind:this={renderedContent}></div>
