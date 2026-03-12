<script lang="ts" context="module">
	import type { renderToString as katexRenderToString } from 'katex';

	// Module-level singleton: load katex once, share across all KatexRenderer instances
	let katexRenderer: Promise<typeof katexRenderToString> | null = null;
	function getKatexRenderer(): Promise<typeof katexRenderToString> {
		if (!katexRenderer) {
			katexRenderer = Promise.all([
				import('katex'),
				import('katex/contrib/mhchem'),
				import('katex/dist/katex.min.css')
			]).then(([katex]) => katex.renderToString);
		}
		return katexRenderer;
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;

	onMount(async () => {
		renderToString = await getKatexRenderer();
	});
</script>

{#if renderToString}
	{@html renderToString(content, { displayMode, throwOnError: false })}
{/if}
