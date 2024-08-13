<script lang="ts">
	import katex from 'katex';
	import 'katex/contrib/mhchem';
	import 'katex/dist/katex.min.css'; 

	export let content: string;
	export let displayMode: boolean = false;

	let renderedContent: HTMLElement;

	$: {
		if (renderedContent) {
			katex.render(content, renderedContent, {
				displayMode,
				throwOnError: false
			});
		}
	}
</script>

<div bind:this={renderedContent}></div>
