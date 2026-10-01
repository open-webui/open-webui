<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Drawer from '../common/Drawer.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';

	export let show = false;

	let mediaQuery: MediaQueryList;
	let largeScreen = false;
	let panelWidth = 350;

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
		minWidth={350}
		minSiblingWidth={360}
		closeOnDragBelowMinWidth
		className="h-full z-10"
	>
		<div class="flex h-full max-h-full min-h-full">
			<div
				class="w-full bg-white dark:bg-gray-900 z-40 pointer-events-auto overflow-hidden scrollbar-hidden flex flex-col"
			>
				<slot />
			</div>
		</div>
	</ResizableSidePanel>
{/if}
