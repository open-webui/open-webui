<script context="module">
	let savedTab: 'controls' | 'files' | 'overview' = 'controls';
</script>

<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import { slide } from 'svelte/transition';
	import { Pane, PaneResizer } from 'paneforge';
	import { v4 as uuidv4 } from 'uuid';

	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import {
		terminalServers,
		mobile,
		showControls,
		showCallOverlay,
		showArtifacts,
		showEmbeds,
		settings,
		showFileNavPath,
		selectedTerminalId,
		user
	} from '$lib/stores';

	import { uploadFile } from '$lib/apis/files';
	import { toast } from 'svelte-sonner';

	import Controls from './Controls/Controls.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatControls/Embeds.svelte';
	import FileNav from './FileNav.svelte';
	import Overview from './Overview.svelte';

	const i18n = getContext('i18n');

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

	export let pane: Pane | null = null;

	let largeScreen = false;
	let dragged = false;
	let minSize = 0;
	let paneReady = false;

	// Tab state for Controls+Files panel
	let activeTab: 'controls' | 'files' | 'overview' = savedTab;
	$: savedTab = activeTab;
	$: hasMessages = history?.messages && Object.keys(history.messages).length > 0;

	$: showControlsTab = $user?.role === 'admin' || ($user?.permissions?.chat?.controls ?? true);
	$: showFilesTab = !!$selectedTerminalId;
	$: showOverviewTab = hasMessages;

	// Tab fallback: if active tab becomes hidden, switch to next available
	$: if (!showOverviewTab && activeTab === 'overview') activeTab = 'controls';
	$: if (!showFilesTab && activeTab === 'files') activeTab = 'controls';
	$: if (!showControlsTab && activeTab === 'controls') {
		if (showFilesTab) activeTab = 'files';
		else if (showOverviewTab) activeTab = 'overview';
	}

	// Auto-close if there are no visible tabs
	$: if (!showControlsTab && !showFilesTab && !showOverviewTab) {
		showControls.set(false);
	}

	// Auto-switch to Files tab when display_file is triggered
	$: if ($showFileNavPath) {
		activeTab = 'files';
		showControls.set(true);
	}

	// Auto-open Files tab when a terminal is selected
	$: if ($selectedTerminalId) {
		activeTab = 'files';
		showControls.set(true);
	}

	// Attach a terminal file to the chat input
	const handleTerminalAttach = async (blob: Blob, name: string, contentType: string) => {
		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: blob.size
		};

		files = [...files, fileItem];

		try {
			const file = new File([blob], name, { type: contentType || 'application/octet-stream' });
			const uploaded = await uploadFile(localStorage.token, file);
			if (!uploaded) throw new Error('Upload failed');

			const idx = files.findIndex((f) => f.itemId === tempItemId);
			if (idx !== -1) {
				files[idx] = {
					...fileItem,
					status: 'uploaded',
					file: uploaded,
					id: uploaded.id,
					url: `${uploaded.id}`,
					collection_name: uploaded?.meta?.collection_name
				};
				files = files;
			}
			toast.success($i18n.t('File attached to chat'));
		} catch (e) {
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error($i18n.t('Failed to attach file'));
		}
	};

	export const openPane = () => {
		if (parseInt(localStorage?.chatControlsSize)) {
			const container = document.getElementById('chat-container');
			let size = Math.floor(
				(parseInt(localStorage?.chatControlsSize) / container.clientWidth) * 100
			);
			pane.resize(size);
		} else {
			pane.resize(minSize);
		}
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

	const onMouseDown = () => {
		dragged = true;
	};
	const onMouseUp = () => {
		dragged = false;
	};

	onMount(() => {
		const mediaQuery = window.matchMedia('(min-width: 1024px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		let resizeObserver: ResizeObserver | null = null;
		let isDestroyed = false;

		// Wait for Svelte to render the Pane after largeScreen changed
		const init = async () => {
			await tick();

			if (isDestroyed) return;

			// If controls were persisted as open, set the pane to the saved size
			if ($showControls && pane) {
				openPane();
			}

			setTimeout(() => {
				paneReady = true;
			}, 0);

			const container = document.getElementById('chat-container') as HTMLElement;
			if (!container) return;

			minSize = Math.floor((350 / container.clientWidth) * 100);
			resizeObserver = new ResizeObserver((entries) => {
				for (let entry of entries) {
					const width = entry.contentRect.width;
					minSize = Math.floor((350 / width) * 100);
					if ($showControls) {
						if (pane && pane.isExpanded() && pane.getSize() < minSize) {
							pane.resize(minSize);
						} else {
							let size = Math.floor(
								(parseInt(localStorage?.chatControlsSize) / container.clientWidth) * 100
							);
							if (size < minSize && pane) pane.resize(minSize);
						}
					}
				}
			});
			resizeObserver.observe(container);
		};
		init();

		document.addEventListener('mousedown', onMouseDown);
		document.addEventListener('mouseup', onMouseUp);

		return () => {
			isDestroyed = true;
			paneReady = false;
			resizeObserver?.disconnect();
			if (!largeScreen) {
				showControls.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
			document.removeEventListener('mousedown', onMouseDown);
			document.removeEventListener('mouseup', onMouseUp);
		}
	});

	const closeHandler = () => {
		if (!largeScreen) {
			showControls.set(false);
		}
		showArtifacts.set(false);
		showEmbeds.set(false);
		if ($showCallOverlay) showCallOverlay.set(false);
	};

	$: if (paneReady && !chatId) closeHandler();

	// Helper: is a "special" full-screen panel active?
	$: specialPanel = $showCallOverlay || $showArtifacts || $showEmbeds;
</script>

{#if !largeScreen}
	{#if $showControls}
		<Drawer
			show={$showControls}
			onClose={() => showControls.set(false)}
			className="min-h-[100dvh] !bg-white dark:!bg-gray-850"
		>
			<div class="h-[100dvh] flex flex-col">
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
							on:close={() => showControls.set(false)}
						/>
					</div>
				{:else if $showEmbeds}
					<Embeds />
				{:else if $showArtifacts}
					<Artifacts {history} />
				{:else}
					<!-- Controls + Files tabs -->
					<div class="flex flex-col h-full min-h-0">
						<!-- Tab bar -->
						<div class="flex items-center justify-between px-2 pt-2.5 pb-2 shrink-0">
							<div class="flex gap-1">
								{#if showControlsTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'controls'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'controls')}
									>
										{$i18n.t('Controls')}
									</button>
								{/if}
								{#if showFilesTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'files'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'files')}
									>
										{$i18n.t('Files')}
									</button>
								{/if}
								{#if showOverviewTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'overview'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'overview')}
									>
										{$i18n.t('Overview')}
									</button>
								{/if}
							</div>
							<button
								class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
								on:click={() => showControls.set(false)}
								aria-label={$i18n.t('Close')}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									class="size-4"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
								</svg>
							</button>
						</div>

						<div
							class="flex-1 min-h-0 {activeTab === 'overview'
								? 'h-full'
								: activeTab === 'controls'
									? 'overflow-y-auto px-3 pt-1'
									: 'overflow-y-auto'}"
						>
							{#if activeTab === 'overview'}
								<Overview
									{history}
									onNodeClick={(e) => {
										const node = e.node;
										showMessage(node.data.message, true);
									}}
									onClose={() => showControls.set(false)}
								/>
							{:else if activeTab === 'files' && $selectedTerminalId}
								<FileNav onAttach={handleTerminalAttach} />
							{:else}
								<Controls embed={true} {models} bind:chatFiles bind:params />
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</Drawer>
	{/if}
{:else}
	{#if $showControls}
		<PaneResizer
			class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20"
			id="controls-resizer"
		>
			<div
				class="absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
			/>
		</PaneResizer>
	{/if}

	<Pane
		bind:pane
		defaultSize={0}
		onResize={(size) => {
			if ($showControls && pane.isExpanded()) {
				if (size < minSize) pane.resize(minSize);
				if (size < minSize) {
					localStorage.chatControlsSize = 0;
				} else {
					const container = document.getElementById('chat-container');
					localStorage.chatControlsSize = Math.floor((size / 100) * container.clientWidth);
				}
			}
		}}
		onCollapse={() => {
			if (paneReady) showControls.set(false);
		}}
		collapsible={true}
		class="z-10 bg-white dark:bg-gray-850"
	>
		{#if $showControls}
			<div class="flex max-h-full min-h-full">
				<div
					class="w-full {specialPanel && !$showCallOverlay
						? ' '
						: 'bg-white dark:shadow-lg dark:bg-gray-850'} z-40 pointer-events-auto overflow-y-auto scrollbar-hidden"
					id="controls-container"
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
								on:close={() => showControls.set(false)}
							/>
						</div>
					{:else if $showEmbeds}
						<Embeds overlay={dragged} />
					{:else if $showArtifacts}
						<Artifacts {history} overlay={dragged} />
					{:else}
						<!-- Controls + Files tabs -->
						<div class="flex flex-col h-full min-h-0">
							<!-- Tab bar -->
							<div class="flex items-center justify-between px-2 pt-2.5 pb-2 shrink-0">
								<div class="flex gap-1">
									{#if showControlsTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'controls'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'controls')}
										>
											{$i18n.t('Controls')}
										</button>
									{/if}
									{#if showFilesTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'files'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'files')}
										>
											{$i18n.t('Files')}
										</button>
									{/if}
									{#if showOverviewTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition {activeTab === 'overview'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'overview')}
										>
											{$i18n.t('Overview')}
										</button>
									{/if}
								</div>
								<button
									class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
									on:click={() => showControls.set(false)}
									aria-label={$i18n.t('Close')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-4"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
									</svg>
								</button>
							</div>

							<div
								class="flex-1 min-h-0 {activeTab === 'overview'
									? 'h-full'
									: activeTab === 'controls'
										? 'overflow-y-auto px-3 pt-1'
										: 'overflow-y-auto'}"
							>
								{#if activeTab === 'overview'}
									<Overview
										{history}
										onNodeClick={(e) => {
											const node = e.node;
											if (node?.data?.message?.favorite) {
												history.messages[node.data.message.id].favorite = true;
											} else {
												history.messages[node.data.message.id].favorite = null;
											}
											showMessage(node.data.message, true);
										}}
										onClose={() => showControls.set(false)}
									/>
								{:else if activeTab === 'files' && $selectedTerminalId}
									<FileNav onAttach={handleTerminalAttach} />
								{:else}
									<Controls embed={true} {models} bind:chatFiles bind:params />
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</Pane>
{/if}
