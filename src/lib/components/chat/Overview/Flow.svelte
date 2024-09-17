<script>
	import { theme } from '$lib/stores';
	import { Background, Controls, SvelteFlow, BackgroundVariant } from '@xyflow/svelte';

	export let nodes;
	export let nodeTypes;
	export let edges;
</script>

<SvelteFlow
	{nodes}
	{nodeTypes}
	{edges}
	fitView
	minZoom={0.001}
	colorMode={$theme.includes('dark') ? 'dark' : 'light'}
	nodesDraggable={false}
	on:nodeclick={(event) => console.log('on node click', event.detail.node)}
	oninit={() => {
		console.log('Flow initialized');
	}}
>
	<Controls showLock={false} />
	<Background variant={BackgroundVariant.Dots} />
</SvelteFlow>
