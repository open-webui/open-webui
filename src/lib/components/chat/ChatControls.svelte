<script context="module" lang="ts">
	let savedTab: 'files' | 'comments' = 'files';
</script>

<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import {
		artifactContents,
		config,
		temporaryChatEnabled,
		terminalServers,
		showTabs,
		showOverview,
		showSidebar,
		mobile,
		showCallOverlay,
		showArtifacts,
		showEmbeds,
		settings,
		showFileNavPath,
		selectedTerminalId,
		user,
		visibleControls
	} from '$lib/stores';

	import { commentsRequest, resourceQuery } from '$lib/apis/comments';
	import CommentsPanel, {
		type CommentsRequest
	} from '$lib/components/comments/CommentsPanel.svelte';
	import { page } from '$app/stores';

	import CallPanel from './MessageInput/CallPanel.svelte';
	import Drawer from '../common/Drawer.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatControls/Embeds.svelte';
	import FileNav from './FileNav.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import Overview from './Overview.svelte';
	import Modal from '../common/Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import { isSavedChatId } from '$lib/utils/chatId';

	const i18n = getContext('i18n');

	export let history;
	let sidePanelAvailable = false;

	export let chatId: string | null = null;
	export let terminalContext: TerminalContext | null = null;
	export let chatUser = null;

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

	// Tab state for the side panel
	let activeTab: typeof savedTab = savedTab;
	$: if ($showTabs === 'files' || $showTabs === 'comments') activeTab = $showTabs;
	else if (typeof $showTabs === 'object') activeTab = $showTabs.tab;
	// svelte-ignore reactive_declaration_module_script_dependency
	$: {
		if (activeTab !== 'comments') savedTab = activeTab;
	}

	$: hasMessages = history?.messages && Object.keys(history.messages).length > 0;

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
	$: if (!hasMessages) showOverview.set(false);
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
	$: if (showCommentsTab && $showTabs) loadCommentCount(chatId);
	let linkedComment = '';
	$: if (showCommentsTab && chatId === $page.params.id && $page.url.href !== linkedComment) {
		linkedComment = $page.url.href;
		const comment_id = $page.url.searchParams.get('comment');
		if (comment_id) showTabs.set({ tab: 'comments', comment_id });
	}
	let currentComments: CommentsRequest | null = null;
	$: currentComments =
		showCommentsTab && chatId
			? {
					resource_type: 'chat',
					resource_id: chatId,
					...(typeof $showTabs === 'object' ? $showTabs : {})
				}
			: null;
	$: if ($showTabs === 'files' || $showTabs === 'comments' || typeof $showTabs === 'object') {
		showArtifacts.set(false);
		showEmbeds.set(false);
		showCallOverlay.set(false);
	}
	beforeNavigate(({ from, to }) => {
		if (from?.url.pathname === to?.url.pathname) return;
		showOverview.set(false);
		if (activeTab === 'comments' && $showTabs)
			showTabs.set(to?.route.id === '/(app)/c/[id]' ? 'comments' : false);
	});
	onDestroy(() => {
		++countVersion;
		showOverview.set(false);
	});

	$: showArtifactsTab = ($artifactContents ?? []).length > 0 && $visibleControls['chat.artifacts'];
	$: sidePanelAvailable = showFilesTab || showCommentsTab || showArtifactsTab || specialPanel;

	// Keep the remaining side-pane tabs available after moving Controls into the composer.
	$: if (!showCommentsTab && activeTab === 'comments') activeTab = 'files';
	$: if (!showFilesTab && showCommentsTab && activeTab === 'files') activeTab = 'comments';
	$: if (
		$showTabs &&
		!$showEmbeds &&
		!$showCallOverlay &&
		!showFilesTab &&
		!showCommentsTab &&
		showArtifactsTab
	)
		showArtifacts.set(true);
	$: if (!sidePanelAvailable) showTabs.set(false);

	// Auto-switch to Files tab when display_file is triggered
	$: if ($showFileNavPath && terminalFilesAvailable) {
		activeTab = 'files';
		showTabs.set('files');
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
				showTabs.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
			document.removeEventListener('mousedown', onMouseDown);
			document.removeEventListener('mouseup', onMouseUp);
		};
	});

	const closeHandler = () => {
		if (!largeScreen) {
			showTabs.set(false);
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

<Modal
	bind:show={$showOverview}
	size="full"
	ariaLabel={$i18n.t('Overview')}
	containerClassName="p-2 sm:p-6"
	className="bg-white dark:bg-gray-900 rounded-2xl overflow-hidden"
>
	<div class="flex h-[calc(100dvh-1rem-2px)] sm:h-[calc(100dvh-3rem-2px)] flex-col">
		<div class="flex items-center justify-between px-4 py-3 shrink-0">
			<h2 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Overview')}</h2>
			<button
				class="rounded-lg p-1 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
				aria-label={$i18n.t('Close')}
				on:click={() => showOverview.set(false)}
			>
				<XMark className="size-5" />
			</button>
		</div>
		<div class="flex-1 min-h-0">
			<Overview
				{history}
				{chatUser}
				onNodeClick={(e: any) => {
					const { node } = e;
					history.messages[node.data.message.id].favorite = node.data.message.favorite
						? true
						: null;
					showOverview.set(false);
					showMessage(node.data.message, true);
				}}
			/>
		</div>
	</div>
</Modal>

{#if !largeScreen}
	<MobileSwipePanel
		open={!!$showTabs}
		enabled={$mobile}
		side="right"
		blocked={$showSidebar || !sidePanelAvailable}
		startTarget="#chat-container"
		width={viewportWidth}
		onOpenChange={(open) => showTabs.set(open)}
		let:visible
		let:panelStyle
		let:backdropStyle
	>
		{#if visible}
			<Drawer
				show={true}
				ariaLabel={$i18n.t('Tabs')}
				onClose={() => showTabs.set(false)}
				onRequestClose={() => showTabs.set(false)}
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
								on:close={() => showTabs.set(false)}
							/>
						</div>
					{:else if $showEmbeds}
						<Embeds />
					{:else}
						<!-- Files, Artifacts, and Comments tabs -->
						<div class="flex flex-col h-full min-h-0">
							<!-- Tab bar -->
							<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
								<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
									{#if showFilesTab}
										<button
											class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {!$showArtifacts &&
											activeTab === 'files'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => {
												showArtifacts.set(false);
												showTabs.set('files');
											}}
										>
											{$i18n.t('Files')}
										</button>
									{/if}
									{#if showArtifactsTab}
										<button
											class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {$showArtifacts
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => {
												showTabs.set(true);
												showArtifacts.set(true);
											}}
										>
											{$i18n.t('Artifacts')}
										</button>
									{/if}
									{#if showCommentsTab}
										<button
											class="inline-flex items-center justify-center gap-1 px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {!$showArtifacts &&
											activeTab === 'comments'
												? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
												: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
											on:click={() => showTabs.set('comments')}
										>
											{$i18n.t('Comments')}{#if commentCount !== null && commentCount > 0}<span
													class="text-[0.8125rem] leading-none text-gray-400/70 dark:text-gray-500/70"
													>{commentCount}</span
												>{/if}
										</button>
									{/if}
								</div>
								<button
									class="py-1 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 px-0"
									on:click={() => showTabs.set(false)}
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

							<div class="flex-1 min-h-0">
								{#if $showArtifacts}
									<Artifacts {history} />
								{:else if activeTab === 'comments'}
									{#if currentComments}
										{#key `${$user.id}:${chatId}:${currentComments.comment_id ?? ''}`}
											<CommentsPanel
												embedded={true}
												bind:view={currentComments}
												onCountChange={setCommentCount}
											/>
										{/key}
									{/if}
								{:else if activeTab === 'files' && terminalFilesAvailable && $selectedTerminalId}
									<FileNav {onAskFile} {chatId} bind:terminalContext />
								{:else if activeTab === 'files' && codeInterpreterEnabled}
									<PyodideFileNav />
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
		open={!!$showTabs}
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
							on:close={() => showTabs.set(false)}
						/>
					</div>
				{:else if $showEmbeds}
					<Embeds overlay={dragged} />
				{:else}
					<!-- Files, Artifacts, and Comments tabs -->
					<div class="flex flex-col h-full min-h-0">
						<!-- Tab bar -->
						<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
							<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
								{#if showFilesTab}
									<button
										class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {!$showArtifacts &&
										activeTab === 'files'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => {
											showArtifacts.set(false);
											showTabs.set('files');
										}}
									>
										{$i18n.t('Files')}
									</button>
								{/if}
								{#if showArtifactsTab}
									<button
										class="px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {$showArtifacts
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => {
											showTabs.set(true);
											showArtifacts.set(true);
										}}
									>
										{$i18n.t('Artifacts')}
									</button>
								{/if}
								{#if showCommentsTab}
									<button
										class="inline-flex items-center justify-center gap-1 px-2.5 py-0.5 text-sm rounded-lg transition whitespace-nowrap {!$showArtifacts &&
										activeTab === 'comments'
											? 'bg-gray-100/40 dark:bg-gray-800/25 font-normal text-gray-700 dark:text-gray-200'
											: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
										on:click={() => showTabs.set('comments')}
									>
										{$i18n.t('Comments')}{#if commentCount !== null && commentCount > 0}<span
												class="text-[0.8125rem] leading-none text-gray-400/70 dark:text-gray-500/70"
												>{commentCount}</span
											>{/if}
									</button>
								{/if}
							</div>
							<button
								class="py-1 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 px-0"
								on:click={() => showTabs.set(false)}
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

						<div class="flex-1 min-h-0">
							{#if $showArtifacts}
								<Artifacts {history} overlay={dragged} />
							{:else if activeTab === 'comments'}
								{#if currentComments}
									{#key `${$user.id}:${chatId}:${currentComments.comment_id ?? ''}`}
										<CommentsPanel
											embedded={true}
											bind:view={currentComments}
											onCountChange={setCommentCount}
										/>
									{/key}
								{/if}
							{:else if activeTab === 'files' && terminalFilesAvailable && $selectedTerminalId}
								<FileNav {onAskFile} overlay={dragged} {chatId} bind:terminalContext />
							{:else if activeTab === 'files' && codeInterpreterEnabled}
								<PyodideFileNav overlay={dragged} />
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</ResizableSidePanel>
{/if}
