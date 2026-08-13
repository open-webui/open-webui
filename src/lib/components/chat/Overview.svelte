<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';

	import View from './Overview/View.svelte';

	export let history;
	export let onNodeClick;
</script>

<SvelteFlowProvider>
	<View {history} {onNodeClick} />
</SvelteFlowProvider>
