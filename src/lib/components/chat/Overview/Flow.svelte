<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import { theme } from '$lib/stores';
	import { Background, Controls, SvelteFlow, BackgroundVariant } from '@xyflow/svelte';

	let { nodes, nodeTypes, edges } = $props();
</script>

<SvelteFlow
	colorMode={$theme.includes('dark')
		? 'dark'
		: $theme === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
				? 'dark'
				: 'light'
			: 'light'}
	{edges}
	fitView
	minZoom={0.001}
	{nodeTypes}
	{nodes}
	nodesConnectable={false}
	nodesDraggable={false}
	oninit={() => {
		console.log('Flow initialized');
	}}
	on:nodeclick={(e) => dispatch('nodeclick', e.detail)}
>
	<Controls showLock={false} />
	<Background variant={BackgroundVariant.Dots} />
</SvelteFlow>
