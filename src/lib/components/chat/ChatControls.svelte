<script context="module" lang="ts">
	let savedTab: 'controls' | 'files' | 'overview' = 'controls';
</script>

<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import {
		config,
		temporaryChatEnabled,
		terminalServers,
		showControls,
		showSidebar,
		mobile,
		showCallOverlay,
		showArtifacts,
		showEmbeds,
		settings,
		showFileNavPath,
		selectedTerminalId,
		user
	} from '$lib/stores';

	import { commentsRequest, resourceQuery } from '$lib/apis/comments';
	import CommentsPanel, {
		type CommentsRequest
	} from '$lib/components/comments/CommentsPanel.svelte';
	import { page } from '$app/stores';

	import Controls from './Controls/Controls.svelte';
	import CallPanel from './MessageInput/CallPanel.svelte';
	import Drawer from '../common/Drawer.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatControls/Embeds.svelte';
	import FileNav from './FileNav.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import Overview from './Overview.svelte';
	import { isSavedChatId } from '$lib/utils/chatId';

	const i18n = getContext('i18n');

	export let history;
	export let models = [];

	export let chatId: string | null = null;
	export let terminalContext: TerminalContext | null = null;
	export let chatUser = null;

	export let chatFiles = [];
	export let params = {};
	export let onParamChange: (key: string, value: unknown) => void = () => {};

	export let bridge: import('$lib/utils/realtime').RealtimeCall;
	export let callMode = 'current';
	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let onAskFile:
		| ((instruction: string, file: import('$lib/apis/terminal').FilesystemFile) => Promise<void>)
		| null = null;
	export let stopResponse: Function;
	export let showMessage: Function;
	export let files;
	export let modelId;

	export let codeInterpreterEnabled = false;

	let largeScreen = false;
	let dragged = false;
	let mounted = false;
	let controlsWidth = 300;
	let viewportWidth = 0;

	// Tab state for Controls+Files panel
	let activeTab: typeof savedTab | 'comments' = savedTab;
	$: if (typeof $showControls === 'string') activeTab = $showControls;
	else if (typeof $showControls === 'object') activeTab = $showControls.tab;
	// svelte-ignore reactive_declaration_module_script_dependency
	$: {
		if (activeTab !== 'comments') savedTab = activeTab;
	}

	$: hasMessages = history?.messages && Object.keys(history.messages).length > 0;

	$: showControlsTab = $user?.role === 'admin' || ($user?.permissions?.chat?.controls ?? true);
	const chatContext = (terminal: any) => terminal?.contexts?.chat ?? {};
	const chatContextAvailable = (terminal: any) => chatContext(terminal) !== false;
	const chatContextNeedsSavedChat = (terminal: any) =>
		chatContext(terminal)?.context_id === 'chat_id';
	$: selectedSystemTerminal = ($terminalServers ?? []).find(
		(t) => t.id && t.id === $selectedTerminalId
	);
	$: selectedSystemTerminalAvailable =
		selectedSystemTerminal &&
		chatContextAvailable(selectedSystemTerminal) &&
		!(chatContextNeedsSavedChat(selectedSystemTerminal) && !isSavedChatId(chatId));
	$: terminalFilesAvailable = !!(
		$config?.features?.enable_tool_servers &&
		$selectedTerminalId &&
		(selectedSystemTerminalAvailable ||
			(!selectedSystemTerminal &&
				$config?.features?.enable_direct_integrations &&
				($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true))))
	);
	$: showFilesTab =
		terminalFilesAvailable ||
		(codeInterpreterEnabled && $config?.code?.interpreter_engine !== 'jupyter');
	$: showOverviewTab = hasMessages;
	$: showCommentsTab = !!(
		$config?.features?.enable_comments &&
		$user &&
		isSavedChatId(chatId) &&
		!$temporaryChatEnabled
	);
	let commentCount: number | null = null;
	let countVersion = 0;
	const setCommentCount = (total: number) => {
		++countVersion;
		commentCount = total;
	};
	const loadCommentCount = async (id: string) => {
		const version = ++countVersion;
		commentCount = null;
		try {
			const result = await commentsRequest<{ total: number }>(
				`/?${resourceQuery({ resource_type: 'chat', resource_id: id })}&limit=1`
			);
			if (version === countVersion) commentCount = result.total;
		} catch {
			/* The comments panel handles access errors when opened. */
		}
	};
	$: if (showCommentsTab && $showControls) loadCommentCount(chatId);
	let linkedComment = '';
	$: if (showCommentsTab && chatId === $page.params.id && $page.url.href !== linkedComment) {
		linkedComment = $page.url.href;
		const comment_id = $page.url.searchParams.get('comment');
		if (comment_id) showControls.set({ tab: 'comments', comment_id });
	}
	let currentComments: CommentsRequest | null = null;
	$: currentComments =
		showCommentsTab && chatId
			? {
					resource_type: 'chat',
					resource_id: chatId,
					...(typeof $showControls === 'object' ? $showControls : {})
				}
			: null;
	$: if ($showControls === 'comments' || typeof $showControls === 'object') {
		showArtifacts.set(false);
		showEmbeds.set(false);
		showCallOverlay.set(false);
	}
	beforeNavigate(({ from, to }) => {
		if (from?.url.pathname === to?.url.pathname) return;
		if (activeTab === 'comments' && $showControls)
			showControls.set(to?.route.id === '/(app)/c/[id]' ? 'comments' : false);
	});
	onDestroy(() => {
		++countVersion;
	});

	// Tab fallback: if active tab becomes hidden, switch to next available
	$: if (!showCommentsTab && activeTab === 'comments') activeTab = 'controls';
	$: if (!showOverviewTab && activeTab === 'overview') activeTab = 'controls';
	$: if (!showFilesTab && activeTab === 'files') activeTab = 'controls';
	$: if (!showControlsTab && activeTab === 'controls') {
		if (showFilesTab) activeTab = 'files';
		else if (showOverviewTab) activeTab = 'overview';
		else if (showCommentsTab && $showControls) showControls.set('comments');
	}

	// Auto-close if there are no visible tabs
	$: if (!showControlsTab && !showFilesTab && !showOverviewTab && !showCommentsTab) {
		showControls.set(false);
	}

	// Auto-switch to Files tab when display_file is triggered
	$: if ($showFileNavPath && terminalFilesAvailable) {
		activeTab = 'files';
		showControls.set('files');
	}

	// Clear selected direct terminal if user lost permission
	$: if (
		$selectedTerminalId &&
		$terminalServers !== null &&
		!($terminalServers ?? []).some((t) => t.id && t.id === $selectedTerminalId) &&
		!(
			$config?.features?.enable_direct_integrations &&
			($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true))
		)
	) {
		selectedTerminalId.set(null);
	}

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
		}
	};

	const onMouseDown = () => {
		dragged = true;
	};
	const onMouseUp = () => {
		dragged = false;
	};

	onMount(() => {
		const mediaQuery = window.matchMedia('(min-width: 768px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		let isDestroyed = false;

		const init = async () => {
			await tick();

			if (isDestroyed) return;

			setTimeout(() => {
				mounted = true;
			}, 0);
		};
		init();

		document.addEventListener('mousedown', onMouseDown);
		document.addEventListener('mouseup', onMouseUp);

		return () => {
			isDestroyed = true;
			mounted = false;
			if (!largeScreen) {
				showControls.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
			document.removeEventListener('mousedown', onMouseDown);
			document.removeEventListener('mouseup', onMouseUp);
		};
	});

	const closeHandler = () => {
		if (!largeScreen) {
			showControls.set(false);
		}
		showArtifacts.set(false);
		showEmbeds.set(false);
		if ($showCallOverlay) showCallOverlay.set(false);
	};

	$: if (mounted && !chatId) closeHandler();

	// Helper: is a "special" full-screen panel active?
	$: specialPanel = $showCallOverlay || $showArtifacts || $showEmbeds;
</script>

<svelte:window bind:innerWidth={viewportWidth} />

{#if !largeScreen}
	<MobileSwipePanel
		open={!!$showControls}
		enabled={$mobile}
		side="right"
		blocked={$showSidebar ||
			(!showControlsTab && !showFilesTab && !showOverviewTab && !showCommentsTab)}
		startTarget="#chat-container"
		width={viewportWidth}
		onOpenChange={(open) => showControls.set(open)}
		let:visible
		let:panelStyle
		let:backdropStyle
	>
		{#if visible}
			<Drawer
				show={true}
				onClose={() => showControls.set(false)}
				onRequestClose={() => showControls.set(false)}
				panelStyle={$mobile ? panelStyle : ''}
				backdropStyle={$mobile ? backdropStyle : ''}
				swipeSide={$mobile ? 'right' : undefined}
				className="min-h-[100dvh] !bg-white dark:!bg-gray-850"
			>
				<div class="h-[100dvh] flex flex-col">
					{#if $showCallOverlay}
						<div
							class="h-full max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
						>
							<CallPanel
								{bridge}
								bind:callMode
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
							<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
								<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
									{#if showControlsTab}
										<button
											class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'controls'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => showControls.set('controls')}
										>
											{$i18n.t('Controls')}
										</button>
									{/if}
									{#if showCommentsTab}
										<button
											class="inline-flex items-center justify-center gap-1 px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'comments'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => showControls.set('comments')}
										>
											{$i18n.t('Comments')}{#if commentCount !== null && commentCount > 0}<span
													class="text-[0.8125rem] leading-none text-gray-400/70 dark:text-gray-500/70"
													>{commentCount}</span
												>{/if}
										</button>
									{/if}
									{#if showFilesTab}
										<button
											class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'files'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => showControls.set('files')}
										>
											{$i18n.t('Files')}
										</button>
									{/if}
									{#if showOverviewTab}
										<button
											class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'overview'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => showControls.set('overview')}
										>
											{$i18n.t('Overview')}
										</button>
									{/if}
								</div>
								<button
									class="py-1 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 px-0"
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
										: ''}"
							>
								{#if activeTab === 'comments'}
									{#if currentComments}
										{#key `${$user.id}:${chatId}:${currentComments.comment_id ?? ''}`}
											<CommentsPanel
												embedded={true}
												bind:view={currentComments}
												onCountChange={setCommentCount}
											/>
										{/key}
									{/if}
								{:else if activeTab === 'overview'}
									<Overview
										{history}
										{chatUser}
										onNodeClick={(e) => {
											const node = e.node;
											showMessage(node.data.message, true);
										}}
									/>
								{:else if activeTab === 'files' && terminalFilesAvailable && $selectedTerminalId}
									<FileNav {onAskFile} {chatId} bind:terminalContext />
								{:else if activeTab === 'files' && codeInterpreterEnabled}
									<PyodideFileNav />
								{:else}
									<Controls embed={true} {models} bind:chatFiles bind:params {onParamChange} />
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</Drawer>
		{/if}
	</MobileSwipePanel>
{:else}
	<ResizableSidePanel
		open={!!$showControls}
		bind:width={controlsWidth}
		minWidth={280}
		minSiblingWidth={360}
		storageKey="chatControlsSize"
		className="h-full z-10 bg-white dark:bg-gray-900"
	>
		<div class="flex h-full max-h-full min-h-full">
			<div
				class="w-full {specialPanel && !$showCallOverlay
					? ' '
					: 'bg-white dark:bg-gray-900'} z-40 pointer-events-auto {activeTab === 'files'
					? ''
					: 'overflow-y-auto'} scrollbar-hidden"
				id="controls-container"
			>
				{#if $showCallOverlay}
					<div class="w-full h-full flex justify-center">
						<CallPanel
							{bridge}
							bind:callMode
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
						<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
							<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
								{#if showControlsTab}
									<button
										class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'controls'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => showControls.set('controls')}
									>
										{$i18n.t('Controls')}
									</button>
								{/if}
								{#if showCommentsTab}
									<button
										class="inline-flex items-center justify-center gap-1 px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'comments'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => showControls.set('comments')}
									>
										{$i18n.t('Comments')}{#if commentCount !== null && commentCount > 0}<span
												class="text-[0.8125rem] leading-none text-gray-400/70 dark:text-gray-500/70"
												>{commentCount}</span
											>{/if}
									</button>
								{/if}
								{#if showFilesTab}
									<button
										class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'files'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => showControls.set('files')}
									>
										{$i18n.t('Files')}
									</button>
								{/if}
								{#if showOverviewTab}
									<button
										class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'overview'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => showControls.set('overview')}
									>
										{$i18n.t('Overview')}
									</button>
								{/if}
							</div>
							<button
								class="py-1 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 px-0"
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
									: ''}"
						>
							{#if activeTab === 'comments'}
								{#if currentComments}
									{#key `${$user.id}:${chatId}:${currentComments.comment_id ?? ''}`}
										<CommentsPanel
											embedded={true}
											bind:view={currentComments}
											onCountChange={setCommentCount}
										/>
									{/key}
								{/if}
							{:else if activeTab === 'overview'}
								<Overview
									{history}
									{chatUser}
									onNodeClick={(e) => {
										const node = e.node;
										if (node?.data?.message?.favorite) {
											history.messages[node.data.message.id].favorite = true;
										} else {
											history.messages[node.data.message.id].favorite = null;
										}
										showMessage(node.data.message, true);
									}}
								/>
							{:else if activeTab === 'files' && terminalFilesAvailable && $selectedTerminalId}
								<FileNav {onAskFile} overlay={dragged} {chatId} bind:terminalContext />
							{:else if activeTab === 'files' && codeInterpreterEnabled}
								<PyodideFileNav overlay={dragged} />
							{:else}
								<Controls embed={true} {models} bind:chatFiles bind:params {onParamChange} />
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</ResizableSidePanel>
{/if}
