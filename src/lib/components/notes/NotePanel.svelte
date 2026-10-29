<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Drawer from '../common/Drawer.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';

	export let show = false;
	export let side: 'left' | 'right' = 'right';
	export let panelWidth = 350;
	export let minWidth = 350;
	export let closeOnDragBelowMinWidth = true;
	export let resizerId = 'controls-resizer';
	export let storageKey = '';
	export let floating = false;

	let mediaQuery: MediaQueryList;
	let largeScreen = false;

	const handleMediaQuery = (e: MediaQueryListEvent | MediaQueryList) => {
		largeScreen = e.matches;
	};

	onMount(() => {
		mediaQuery = window.matchMedia('(min-width: 1000px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		mediaQuery?.removeEventListener('change', handleMediaQuery);
	});
</script>

{#if !largeScreen}
	{#if show}
		<Drawer
			{show}
			onClose={() => {
				show = false;
			}}
		>
			<div class="h-screen max-h-dvh flex flex-col">
				<slot />
			</div>
		</Drawer>
	{/if}
{:else}
	<ResizableSidePanel
		bind:open={show}
		bind:width={panelWidth}
		{minWidth}
		{side}
		{resizerId}
		{storageKey}
		subtleDivider={floating}
		minSiblingWidth={360}
		{closeOnDragBelowMinWidth}
		className="h-full z-10"
	>
		<div class="flex h-full max-h-full min-h-full">
			<div
				class="w-full z-40 pointer-events-auto overflow-hidden scrollbar-hidden flex flex-col {floating
					? ''
					: 'bg-white dark:bg-gray-900'}"
			>
				<slot />
			</div>
		</div>
	</ResizableSidePanel>
{/if}
