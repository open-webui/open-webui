<script>
	import { getContext } from 'svelte';

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
	export let viewportPinned = false;
	export let onNodeClick;
</script>

<SvelteFlow
	{nodes}
	{nodeTypes}
	{edges}
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
	on:nodeclick={(e) => onNodeClick?.(e.detail)}
	oninit={() => {}}
>
	<Controls showLock={false}>
		<ControlButton
			on:click={() => (viewportPinned = !viewportPinned)}
			title={viewportPinned ? $i18n.t('Viewport Pinned') : $i18n.t('Viewport Unpinned')}
		>
			{#if viewportPinned}
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
