<script lang="ts">
	import { Pane, PaneResizer } from 'paneforge';
	import { onMount, tick } from 'svelte';

	import { mobile, realtimeClientConfig, showCallOverlay } from '$lib/stores';

	import Drawer from '../common/Drawer.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import RealtimeOverlay from './MessageInput/RealtimeOverlay.svelte';
	import { modelHasRealtimeCapability } from './MessageInput/realtime/model-capabilities';

	export let models = [];
	export let modelId = '';
	export let chatId = null;
	export let selectedToolIds: string[] = [];
	export let toolServers = [];
	export let features = {};
	export let sessionId: string | null = null;
	export let terminalId: string | null = null;
	export let systemPrompt = '';
	export let files = [];
	export let submitPrompt: Function = () => {};
	export let stopResponse: Function = () => {};
	export let eventTarget: EventTarget;

	let pane: Pane | null = null;
	let minSize = 0;
	let initialPaneSize = 28;
	let wasOpen = false;

	const useRealtimeOverlay = () =>
		$showCallOverlay && modelHasRealtimeCapability(models, modelId, $realtimeClientConfig);

	const closeOverlay = () => {
		showCallOverlay.set(false);
	};

	const openPane = () => {
		if (!pane) {
			return;
		}

		const container = document.getElementById('chat-container');
		if (!container) {
			return;
		}

		const savedWidth = parseInt(localStorage?.chatVoiceOverlaySize ?? '0');
		const savedSize = savedWidth ? Math.floor((savedWidth / container.clientWidth) * 100) : minSize;
		const nextSize = Math.max(savedSize || minSize, minSize || 0);

		if (nextSize > 0) {
			pane.resize(nextSize);
		}
	};

	onMount(() => {
		let resizeObserver: ResizeObserver | null = null;
		const container = document.getElementById('chat-container') as HTMLElement | null;

		if (container) {
			minSize = Math.floor((350 / container.clientWidth) * 100);
			initialPaneSize = Math.max(minSize || 0, 28);
			resizeObserver = new ResizeObserver((entries) => {
				for (const entry of entries) {
					const width = entry.contentRect.width;
					minSize = Math.floor((350 / width) * 100);
					initialPaneSize = Math.max(minSize || 0, 28);
					if ($showCallOverlay && pane && pane.isExpanded() && pane.getSize() < minSize) {
						pane.resize(minSize);
					}
				}
			});
			resizeObserver.observe(container);
		}

		return () => {
			resizeObserver?.disconnect();
		};
	});

	$: if ($showCallOverlay && !$mobile) {
		if (!wasOpen) {
			wasOpen = true;
			tick().then(() => openPane());
		}
	} else {
		wasOpen = false;
	}
</script>

{#if $mobile}
	{#if $showCallOverlay}
		<Drawer
			show={$showCallOverlay}
			onClose={closeOverlay}
			className="min-h-[100dvh] !bg-white dark:!bg-gray-850"
		>
			<div class="h-[100dvh] flex flex-col bg-white text-gray-700 dark:bg-black dark:text-gray-300">
				{#if useRealtimeOverlay()}
					<RealtimeOverlay
						{modelId}
						{chatId}
						{selectedToolIds}
						{toolServers}
						{features}
						{sessionId}
						{terminalId}
						{systemPrompt}
						on:close={closeOverlay}
					/>
				{:else}
					<CallOverlay
						bind:files
						{submitPrompt}
						{stopResponse}
						{modelId}
						{chatId}
						{eventTarget}
						on:close={closeOverlay}
					/>
				{/if}
			</div>
		</Drawer>
	{/if}
{:else if $showCallOverlay}
	<PaneResizer
		class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20"
		id="voice-overlay-resizer"
	>
		<div
			class="absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
		/>
	</PaneResizer>

	<Pane
		bind:pane
		defaultSize={initialPaneSize}
		onResize={(size) => {
			if ($showCallOverlay && pane?.isExpanded()) {
				const container = document.getElementById('chat-container');
				if (container) {
					localStorage.chatVoiceOverlaySize = Math.floor((size / 100) * container.clientWidth);
				}
			}
		}}
		onCollapse={() => {
			closeOverlay();
		}}
		collapsible={true}
		class="z-10 bg-white dark:bg-gray-850"
	>
		<div
			class="w-full h-full flex justify-center bg-white text-gray-700 dark:bg-black dark:text-gray-300"
		>
			{#if useRealtimeOverlay()}
				<RealtimeOverlay
					{modelId}
					{chatId}
					{selectedToolIds}
					{toolServers}
					{features}
					{sessionId}
					{terminalId}
					{systemPrompt}
					on:close={closeOverlay}
				/>
			{:else}
				<CallOverlay
					bind:files
					{submitPrompt}
					{stopResponse}
					{modelId}
					{chatId}
					{eventTarget}
					on:close={closeOverlay}
				/>
			{/if}
		</div>
	</Pane>
{/if}
