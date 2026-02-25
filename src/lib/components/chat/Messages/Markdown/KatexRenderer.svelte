<script lang="ts" context="module">
	import type { renderToString as katexRenderToString } from 'katex';

	// Module-level singleton: load katex once, share across all KatexRenderer instances
	let katexReady: Promise<typeof katexRenderToString> | null = null;
	function getKatex(): Promise<typeof katexRenderToString> {
		if (!katexReady) {
			katexReady = Promise.all([
				import('katex'),
				import('katex/contrib/mhchem'),
				import('katex/dist/katex.min.css')
			]).then(([katex]) => katex.renderToString);
		}
		return katexReady;
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;

	onMount(async () => {
		renderToString = await getKatex();
	});
</script>

{#if renderToString}
	{@html renderToString(content, { displayMode, throwOnError: false })}
{/if}

