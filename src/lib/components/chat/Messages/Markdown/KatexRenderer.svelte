<script lang="ts">
	import type { renderToString as katexRenderToString } from 'katex';
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;

	onMount(async () => {
		const [katex] = await Promise.all([
			import('katex'),
			import('katex/contrib/mhchem'),
			import('katex/dist/katex.min.css')
		]);
		renderToString = katex.renderToString;
	});
</script>

{#if renderToString}
	{@html renderToString(content, { displayMode, throwOnError: false })}
{/if}
