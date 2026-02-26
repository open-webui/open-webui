<script lang="ts">
	import type renderToStringType from '$lib/utils/katex';
	import { onMount } from 'svelte';
	import { getContextAsyncTaskTracker } from '$lib/utils/AsyncTaskTracker';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof renderToStringType | null = null;
	const asyncTaskTracker = getContextAsyncTaskTracker();

	onMount(async () => {
		const loadKatex = () => import('$lib/utils/katex').then((module) => {
			renderToString = module.default;
		});

		if (asyncTaskTracker) {
			await asyncTaskTracker.track(loadKatex, 'katex-renderer-load');
			return;
		}

		await loadKatex();
	});
</script>

{#if renderToString}
	{@html renderToString(content, { displayMode, throwOnError: false })}
{/if}
