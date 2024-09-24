<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import { slide } from 'svelte/transition';

	import { onDestroy, onMount } from 'svelte';
	import { mobile, showControls, showCallOverlay, showOverview } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Controls from './Controls/Controls.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Overview from './Overview.svelte';
	import { Pane, PaneResizer } from 'paneforge';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import { get } from 'svelte/store';

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
	let largeScreen = false;

	onMount(() => {
		// listen to resize 1024px
		const mediaQuery = window.matchMedia('(min-width: 1024px)');

		const handleMediaQuery = (e) => {
			if (e.matches) {
				largeScreen = true;
			} else {
				largeScreen = false;
				pane = null;
			}
		};

		mediaQuery.addEventListener('change', handleMediaQuery);

		handleMediaQuery(mediaQuery);

		return () => {
			mediaQuery.removeEventListener('change', handleMediaQuery);
		};
	});

	onDestroy(() => {
		showControls.set(false);
	});

	$: if (!chatId) {
		showOverview.set(false);
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
					class=" {$showCallOverlay || $showOverview ? ' h-screen  w-screen' : 'px-6 py-4'} h-full"
				>
					{#if $showCallOverlay}
						<div
							class=" h-full max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
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
		<!-- if $showControls -->
		<PaneResizer class="relative flex w-2 items-center justify-center bg-background group">
			<div class="z-10 flex h-7 w-5 items-center justify-center rounded-sm">
				<EllipsisVertical className="size-4 invisible group-hover:visible" />
			</div>
		</PaneResizer>
		<Pane
			bind:pane
			defaultSize={$showControls
				? parseInt(localStorage?.chatControlsSize ?? '30')
					? parseInt(localStorage?.chatControlsSize ?? '30')
					: 30
				: 0}
			onResize={(size) => {
				if (size === 0) {
					showControls.set(false);
				} else {
					if (!$showControls) {
						showControls.set(true);
					}
					localStorage.chatControlsSize = size;
				}
			}}
		>
			{#if $showControls}
				<div class="pr-4 pb-8 flex max-h-full min-h-full">
					<div
						class="w-full {$showOverview && !$showCallOverlay
							? ' '
							: 'px-5 py-4 bg-white dark:shadow-lg dark:bg-gray-850  border border-gray-50 dark:border-gray-800'}  rounded-lg z-50 pointer-events-auto overflow-y-auto scrollbar-hidden"
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
