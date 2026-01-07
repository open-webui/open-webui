<script lang="ts">
	import type { renderToString as katexRenderToString } from 'katex';
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;
	let renderedHtml: string = '';
	let hasError: boolean = false;

	onMount(async () => {
		const [katex] = await Promise.all([
			import('katex'),
			import('katex/contrib/mhchem'),
			import('katex/dist/katex.min.css')
		]);
		renderToString = katex.renderToString;
	});

	// Render with error logging
	$: if (renderToString && content) {
		try {
			// First try with strict mode to catch warnings
			renderedHtml = renderToString(content, { displayMode, throwOnError: false, strict: 'warn' });

			// Check if rendered output contains error class (KaTeX adds this for errors)
			if (renderedHtml.includes('katex-error')) {
				hasError = true;
				console.error('[KaTeX Rendering Error]', {
					content: content,
					displayMode: displayMode,
					renderedHtml: renderedHtml.substring(0, 200) + '...'
				});
			} else {
				hasError = false;
			}
		} catch (e) {
			hasError = true;
			console.error('[KaTeX Rendering Exception]', {
				content: content,
				displayMode: displayMode,
				error: e
			});
			// Fallback: show raw content
			renderedHtml = `<span class="katex-error">${content}</span>`;
		}
	}
</script>

{#if renderToString && renderedHtml}
	{@html renderedHtml}
{/if}
