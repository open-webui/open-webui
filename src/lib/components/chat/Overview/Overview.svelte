<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import OverviewContent from './OverviewContent.svelte';

	const dispatch = createEventDispatcher();

	export let history;
</script>

<SvelteFlowProvider>
	<OverviewContent
		{history}
		on:nodeclick={(e) => dispatch('nodeclick', e.detail)}
		on:close={() => dispatch('close')}
	/>
</SvelteFlowProvider>
