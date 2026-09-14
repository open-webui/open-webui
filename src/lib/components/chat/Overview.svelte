<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';

	import View from './Overview/View.svelte';

	export let history;
	export let onNodeClick;
	export let chatUser = null;
</script>

<SvelteFlowProvider>
	<View {history} {onNodeClick} {chatUser} />
</SvelteFlowProvider>
