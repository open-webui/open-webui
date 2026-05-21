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
	import { onMount, getContext } from 'svelte';
	import { copyToClipboard } from '$lib/utils';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;

	onMount(async () => {
		renderToString = await getKatexRenderer();
	});
</script>

{#if renderToString}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<svelte:element
		this={displayMode ? 'div' : 'span'}
		class="cursor-pointer"
		on:click={() => {
			copyToClipboard(content);
			toast.success($i18n.t('Copied to clipboard'));
		}}
	>
		{@html renderToString(content, { displayMode, throwOnError: false })}
	</svelte:element>
{/if}
