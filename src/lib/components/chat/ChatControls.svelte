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

	let largeScreen = false;
	onMount(() => {
		// listen to resize 1024px
		const mediaQuery = window.matchMedia('(min-width: 1024px)');

		const handleMediaQuery = (e) => {
			if (e.matches) {
				largeScreen = true;
			} else {
				largeScreen = false;
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
		{#if $showCallOverlay}
			<div class=" absolute w-full h-screen max-h-[100dvh] flex z-[999] overflow-hidden">
				<div
					class="absolute w-full h-screen max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
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
			</div>
		{:else if $showControls}
			<Drawer
				show={$showControls}
				on:close={() => {
					showControls.set(false);
				}}
			>
				<div class=" {$showOverview ? ' h-screen  w-screen' : 'px-6 py-4'} h-full">
					{#if $showOverview}
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
	{:else if $showControls}
		<div class=" absolute bottom-0 right-0 z-20 h-full pointer-events-none">
			<div class="pr-4 pt-14 pb-8 w-[26rem] h-full" in:slide={{ duration: 200, axis: 'x' }}>
				<div
					class="w-full h-full {$showOverview && !$showCallOverlay
						? ' '
						: 'px-5 py-4 bg-white dark:shadow-lg dark:bg-gray-850  border border-gray-50 dark:border-gray-800'}  rounded-lg z-50 pointer-events-auto overflow-y-auto scrollbar-hidden"
				>
					{#if $showCallOverlay}
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
			</div>
		</div>
	{/if}
</SvelteFlowProvider>
