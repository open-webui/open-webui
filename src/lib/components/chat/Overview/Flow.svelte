<script>
	import { createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { theme } from '$lib/stores';
	import {
		Background,
		Controls,
		SvelteFlow,
		BackgroundVariant,
		ControlButton
	} from '@xyflow/svelte';
	import AlignVertical from '$lib/components/icons/AlignVertical.svelte';
	import AlignHorizontal from '$lib/components/icons/AlignHorizontal.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import PinSlash from '$lib/components/icons/PinSlash.svelte';

	export let nodes;
	export let nodeTypes;
	export let edges;
	export let setLayoutDirection;
	export let pinned = false;
</script>

<SvelteFlow
	{nodes}
	{nodeTypes}
	{edges}
	fitView
	minZoom={0.001}
	colorMode={$theme.includes('dark')
		? 'dark'
		: $theme === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
				? 'dark'
				: 'light'
			: 'light'}
	nodesConnectable={false}
	nodesDraggable={false}
	on:nodeclick={(e) => dispatch('nodeclick', e.detail)}
	oninit={() => {
		console.log('Flow initialized');
	}}
>
	<Controls showLock={false}>
		<ControlButton
			on:click={() => (pinned = !pinned)}
			title={pinned ? $i18n.t('Viewport Pinned') : $i18n.t('Viewport Unpinned')}
		>
			{#if pinned}
				<Pin />
			{:else}
				<PinSlash />
			{/if}
		</ControlButton>
		<ControlButton on:click={() => setLayoutDirection('vertical')} title="Vertical Layout">
			<AlignVertical className="size-4" />
		</ControlButton>
		<ControlButton on:click={() => setLayoutDirection('horizontal')} title="Horizontal Layout">
			<AlignHorizontal className="size-4" />
		</ControlButton>
	</Controls>
	<Background variant={BackgroundVariant.Dots} />
</SvelteFlow>
