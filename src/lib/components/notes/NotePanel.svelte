<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { Pane, PaneResizer } from 'paneforge';

	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';

	export let show = false;
	export let pane = null;

	export let containerId = 'note-editor';

	let mediaQuery;
	let largeScreen = false;

	let minSize = 0;

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
			pane = null;
		}
	};

	onMount(() => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		mediaQuery.removeEventListener('change', handleMediaQuery);
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
			<div class=" px-3.5 py-2.5 h-screen">
				<slot />
			</div>
		</Drawer>
	{/if}
{:else if show}
	<PaneResizer
		class="relative flex w-2 items-center justify-center bg-background group bg-white dark:shadow-lg dark:bg-gray-850 border border-gray-100 dark:border-gray-850"
	>
		<div class="z-10 flex h-7 w-5 items-center justify-center rounded-xs">
			<EllipsisVertical className="size-4 invisible group-hover:visible" />
		</div>
	</PaneResizer>

	<Pane
		bind:pane
		defaultSize={30}
		minSize={30}
		onCollapse={() => {
			show = false;
		}}
		collapsible={true}
		class=" z-10 "
	>
		{#if show}
			<div class="flex max-h-full min-h-full">
				<div
					class="w-full pl-1.5 pr-2.5 pt-2 bg-white dark:shadow-lg dark:bg-gray-850 border border-gray-100 dark:border-gray-850 z-40 pointer-events-auto overflow-y-auto scrollbar-hidden"
				>
					<slot />
				</div>
			</div>
		{/if}
	</Pane>
{/if}
