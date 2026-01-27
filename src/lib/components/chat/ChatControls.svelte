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

	let minSize = 30; // Fixed size percentage

	export const openPane = () => {
		isAnimating = true;
		pane.resize(minSize);
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
	};

	$: if (!chatId) {
		closeHandler();
	}
</script>

<SvelteFlowProvider>
	{#if !largeScreen}
		{#if $showControls}
			<Drawer
				show={$showControls}
				on:close={() => {
					showControls.set(false);
				}}
			>
				<div
					class=" {$showCallOverlay || $showOverview || $showArtifacts
						? ' h-screen  w-full'
						: 'px-6 py-4'} h-full"
					in:fade={{ duration: 120, easing: cubicOut }}
					out:fade={{ duration: 100, easing: cubicOut }}
				>
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
									showControls.set(false);
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
			</Drawer>
		{/if}
	{:else}
		<!-- Desktop View -->
		{#if $showControls}
			<!-- Removed PaneResizer - no longer resizable -->
			<div class="w-1 bg-gray-200 dark:bg-gray-700"></div>
		{/if}

		<Pane
			bind:pane
			defaultSize={0}
			minSize={minSize}
			maxSize={minSize}
			onCollapse={() => {
				showControls.set(false);
			}}
			collapsible={true}
			class="z-10 transition-all duration-200 ease-out"
		>
			{#if $showControls}
				<div
					class="flex max-h-full min-h-full"
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
		transition: width 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
	}
</style>