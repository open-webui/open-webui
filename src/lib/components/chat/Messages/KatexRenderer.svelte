<script lang="ts">
	import katex from 'katex';
	import 'katex/contrib/mhchem';

	export let content: string;
	export let displayMode: boolean = false;
</script>

{@html katex.renderToString(content, { displayMode, throwOnError: false })}
