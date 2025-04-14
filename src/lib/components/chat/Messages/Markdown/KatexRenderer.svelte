<script lang="ts">
	import katex from 'katex';
	import 'katex/contrib/mhchem';
	import 'katex/dist/katex.min.css';

	interface Props {
		content: string;
		displayMode?: boolean;
	}

	let { content, displayMode = false }: Props = $props();
</script>

{@html katex.renderToString(content, { displayMode, throwOnError: false })}
