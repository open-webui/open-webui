<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { useSvelteFlow, useNodesInitialized, useStore, SvelteFlowProvider } from '@xyflow/svelte';

	const dispatch = createEventDispatcher();

	import View from './Overview/View.svelte';

	export let history;

	export let onClose;
	export let onNodeClick;
</script>

<SvelteFlowProvider>
	<View {history} {onClose} {onNodeClick} />
</SvelteFlowProvider>
