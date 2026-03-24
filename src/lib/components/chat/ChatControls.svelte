<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import { slide, fade, fly } from 'svelte/transition';
	import { quintOut, cubicOut } from 'svelte/easing';
	import { Pane, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick } from 'svelte';
	import { mobile, showControls, showCallOverlay, showOverview, showArtifacts } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Controls from './Controls/Controls.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Overview from './Overview.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Artifacts from './Artifacts.svelte';
	import { min } from '@floating-ui/utils';

	export let history;
	export let models = [];

	export let chatId = null;

	export let chatFiles = [];
	export let params = {};

	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let stopResponse: Function;
	export let showMessage: Function;
	export let files;
	export let modelId;

	export let pane;

	let mediaQuery;
	let largeScreen = false;
	let dragged = false;
	let isAnimating = false;

	let minSize = 20; // Minimum size percentage (can't pull back smaller than this)
	let maxSize = 70; // Maximum size percentage
	let currentSize = 30; // Default size

	export const openPane = () => {
		isAnimating = true;
		currentSize = 30;
		pane.resize(30);
		setTimeout(() => {
			isAnimating = false;
		}, 150);
	};

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;

			if ($showCallOverlay) {
				showCallOverlay.set(false);
				await tick();
				showCallOverlay.set(true);
			}
		} else {
			largeScreen = false;

			if ($showCallOverlay) {
				showCallOverlay.set(false);
				await tick();
				showCallOverlay.set(true);
			}
			pane = null;
		}
	};

	const onMouseDown = (event) => {
		dragged = true;
	};

	const onMouseUp = (event) => {
		dragged = false;
	};

	onMount(() => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		document.addEventListener('mousedown', onMouseDown);
		document.addEventListener('mouseup', onMouseUp);
	});

	onDestroy(() => {
		showControls.set(false);

		mediaQuery.removeEventListener('change', handleMediaQuery);
		document.removeEventListener('mousedown', onMouseDown);
		document.removeEventListener('mouseup', onMouseUp);
	});

	const closeHandler = () => {
		showControls.set(false);
		showOverview.set(false);
		showArtifacts.set(false);

		if ($showCallOverlay) {
			showCallOverlay.set(false);
		}

		// Reset pane size to default when closing
		if (pane) {
			currentSize = 30;
			pane.resize(0);
		}
	};

	$: if (!chatId) {
		closeHandler();
	}

	// Reset pane when controls are hidden
	$: if (!$showControls && pane) {
		setTimeout(() => {
			pane.resize(0);
		}, 150);
	}

	// Track pane size changes
	$: if (pane && pane.size) {
		currentSize = pane.size;
	}
</script>

<SvelteFlowProvider>
	{#if !largeScreen}
		{#if $showControls}
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="fixed inset-0 z-[999] bg-black/35 backdrop-blur-[1px]"
				in:fade={{ duration: 140, easing: cubicOut }}
				out:fade={{ duration: 100, easing: cubicOut }}
				on:mousedown={closeHandler}
			>
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div
					class="absolute right-0 top-0 h-full max-h-[100dvh] bg-gray-50 dark:bg-gray-900 border-l border-gray-200/90 dark:border-gray-700 shadow-2xl overflow-y-auto scrollbar-hidden {$showCallOverlay ||
					$showOverview ||
					$showArtifacts
						? 'w-full'
						: 'w-[min(90vw,360px)]'}"
					in:fly={{ x: 360, duration: 220, easing: cubicOut }}
					out:fly={{ x: 360, duration: 160, easing: cubicOut }}
					on:mousedown|stopPropagation
				>
					<div class="h-full {$showCallOverlay || $showOverview || $showArtifacts ? '' : 'px-2.5 py-2.5'}">
					{#if $showCallOverlay}
						<div
							class="h-full max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
						>
							<CallOverlay
								bind:files
								{submitPrompt}
								{stopResponse}
								{modelId}
								{chatId}
								{eventTarget}
								on:close={() => {
									closeHandler();
								}}
							/>
						</div>
					{:else if $showArtifacts}
						<Artifacts {history} />
					{:else if $showOverview}
						<Overview
							{history}
							on:nodeclick={(e) => {
								showMessage(e.detail.node.data.message);
							}}
							on:close={() => {
								closeHandler();
							}}
						/>
					{:else}
						<Controls
							on:close={() => {
								closeHandler();
							}}
							{models}
							bind:chatFiles
							bind:params
						/>
					{/if}
					</div>
				</div>
			</div>
		{/if}
	{:else}
		<!-- Desktop View -->
		{#if $showControls}
			<!-- Resizable divider - only show when Artifacts is active -->
			{#if $showArtifacts}
				<PaneResizer
					class="group relative w-1 bg-gray-200 dark:bg-gray-700 hover:bg-orange-500 dark:hover:bg-orange-500 cursor-col-resize select-none"
				>
					<div
						class="absolute inset-y-0 -left-1 -right-1 group-hover:bg-orange-500/20"
					></div>
				</PaneResizer>
			{:else}
				<div class="w-1 bg-gray-200 dark:bg-gray-700"></div>
			{/if}
		{/if}

		<Pane
			bind:pane
			defaultSize={0}
			minSize={minSize}
			maxSize={maxSize}
			onCollapse={() => {
				showControls.set(false);
			}}
			collapsible={true}
			class="z-10"
		>
			{#if $showControls}
				<div
					class="flex max-h-full min-h-full w-full"
					in:fly={{ x: 50, duration: 180, easing: quintOut }}
					out:fly={{ x: 50, duration: 120, easing: cubicOut }}
				>
					<div
						class="w-full {($showOverview || $showArtifacts) && !$showCallOverlay
							? ''
							: 'px-4 py-4 bg-white dark:bg-gray-850 border-l border-gray-200 dark:border-gray-700 shadow-xl dark:shadow-2xl'} z-40 pointer-events-auto overflow-y-auto scrollbar-hidden transition-all duration-200"
						in:fade={{ duration: 150, delay: 50, easing: cubicOut }}
						out:fade={{ duration: 100, easing: cubicOut }}
					>
						{#if $showCallOverlay}
							<div class="w-full h-full flex justify-center">
								<CallOverlay
									bind:files
									{submitPrompt}
									{stopResponse}
									{modelId}
									{chatId}
									{eventTarget}
									on:close={() => {
										showControls.set(false);
									}}
								/>
							</div>
						{:else if $showArtifacts}
							<Artifacts {history} overlay={dragged} />
						{:else if $showOverview}
							<Overview
								{history}
								on:nodeclick={(e) => {
									if (e.detail.node.data.message.favorite) {
										history.messages[e.detail.node.data.message.id].favorite = true;
									} else {
										history.messages[e.detail.node.data.message.id].favorite = null;
									}

									showMessage(e.detail.node.data.message);
								}}
								on:close={() => {
									showControls.set(false);
								}}
							/>
						{:else}
							<Controls
								on:close={() => {
									showControls.set(false);
								}}
								{models}
								bind:chatFiles
								bind:params
							/>
						{/if}
					</div>
				</div>
			{/if}
		</Pane>
	{/if}
</SvelteFlowProvider>

<style>
	:global(.pane) {
		transition: width 0.2s ease-out !important;
	}
	
	:global(.pane-resizer) {
		transition: background-color 0.15s ease-in-out !important;
	}
</style>