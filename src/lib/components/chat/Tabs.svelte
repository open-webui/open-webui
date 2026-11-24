<script lang="ts">
	import type { AppLayoutContext, MachineContext } from '$lib/types';
	import type { GitStatus } from '$lib/apis/machines/git';
	let fileGitStatuses: Record<string, GitStatus | null> = {};
	let fileGitDiffModes: Record<string, 'unified' | 'split'> = {};
	let fileGitHideWhitespace: Record<string, boolean> = {};
	import { onMount, onDestroy, tick, getContext, type ComponentProps } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { get, readable, writable, type Readable, type Writable } from 'svelte/store';
	import {
		chatViewEntry,
		loadChatView,
		changeChatView,
		flushChatView,
		updateViewTab,
		createViewSession,
		promoteChatView,
		registerChatViewCapture,
		chatViewChanges,
		hasChatViewDrafts,
		clearChatViews
	} from '$lib/stores/chatViewStates';
	import { v4 as uuidv4 } from 'uuid';
	import Sortable from 'sortablejs';
	import { beforeNavigate } from '$app/navigation';
	import { WEBUI_NAME } from '$lib/stores';
	import type Chat from './Chat.svelte';
	import { pageTabKey } from './Tabs/tabs';
	import Page from './Tabs/Page.svelte';
	let pageViews: Record<string, Page> = {};
	let pendingPageTab: { href: string; label: string; inSplit?: boolean } | null = null;
	import {
		config,
		embed,
		temporaryChat,
		machines,
		selectedFolder,
		showTabs,
		activeChatTabId,
		chatTabRequest,
		showSidebar,
		mobile,
		voiceCall,
		showEmbeds,
		settings,
		showFileNav,
		showFileNavPath,
		selectedMachineId,
		user,
		visibleControls
	} from '$lib/stores';

	import { commentsRequest, resourceQuery } from '$lib/apis/comments';
	import CommentsPanel, {
		type CommentsRequest
	} from '$lib/components/comments/CommentsPanel.svelte';
	import { page } from '$app/stores';

	import {
		createTabsState,
		openTab,
		openTabInSplit,
		activateTab,
		removeTab,
		moveTab,
		moveTabToGroup,
		splitTab,
		resizeSplit,
		getLayoutRects,
		type TabGroup,
		type GroupRect,
		type SplitDivider,
		type SplitEdge,
		mainChatTabId,
		setMainChatTab,
		setSplitTabs,
		fileTabId,
		type Tab
	} from './Tabs/tabs';
	import {
		resolveMachineTarget,
		machineRequest,
		MachineRequestError,
		type MachineTarget
	} from '$lib/apis/machines';
	import { formatChord, keybindings, matchKeybinding, Shortcut } from '$lib/shortcuts';
	import HotkeyHint from '../common/HotkeyHint.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Dropdown from '../common/Dropdown.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';
	import Icon from './FileNav/Icon.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import FolderIcon from '$lib/components/icons/Folder.svelte';
	import HomeIcon from '$lib/components/icons/Home.svelte';
	import HashtagIcon from '$lib/components/icons/Hashtag.svelte';
	import NotesIcon from '$lib/components/layout/Sidebar/icons/Notes.svelte';
	import WorkspaceIcon from '$lib/components/layout/Sidebar/icons/Workspace.svelte';
	import ClockIcon from '$lib/components/layout/Sidebar/icons/Clock.svelte';
	import CalendarIcon from '$lib/components/layout/Sidebar/icons/Calendar.svelte';
	import CodeIcon from '$lib/components/layout/Sidebar/icons/Code.svelte';
	import { fileIconName } from './FileNav/fileIcon';
	import UntitledFile from './Tabs/UntitledFile.svelte';
	import QuickOpen from './Tabs/QuickOpen.svelte';
	import MachinePicker, { type MachineOption } from './Tabs/MachinePicker.svelte';
	import { machineIdOf, selectMachine } from '$lib/utils/machines';
	import { terminalIconName } from '$lib/utils/terminal';
	import VoiceNote from './Tabs/VoiceNote.svelte';
	import Browser from './Tabs/Browser.svelte';
	import Desktop from './Tabs/Desktop.svelte';
	import XTerminal from './XTerminal.svelte';
	import CallPanel from './MessageInput/CallPanel.svelte';
	import Drawer from '../common/Drawer.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';
	import GitBar from './Tabs/GitBar.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './Tabs/Embeds.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import Knowledge from './Tabs/Knowledge.svelte';
	import ChatTab from './Tabs/ChatTab.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	let stopTerminalChoice: ((stop: boolean) => void) | null = null;
	import SplitPanel from '../icons/SplitPanel.svelte';
	import {
		folderSessionId,
		isFolderSessionId,
		isSavedChatId,
		isTemporaryChatId
	} from '$lib/utils/chatId';
	import { getChatView } from '$lib/apis/chats/view';

	const i18n = getContext<any>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let chatHistory: any = { messages: {}, currentId: null };

	export let chatId: string | null = null;
	export let chatLoading = false;
	export let chatStreaming = false;
	export let folderId: string | null = null;
	export let machineContext: MachineContext | null = null;
	export let chatUser = null;
	export let mainArtifacts: Readable<{ type: string; content: string }[]> = readable([]);

	export let bridge: import('$lib/utils/realtime').RealtimeCall | undefined = undefined;
	export let callMode = 'current';
	export let eventTarget = new EventTarget();
	export let submitPrompt: Function = () => {};
	export let onAskFile:
		| ((instruction: string, file: import('$lib/apis/machines').FilesystemFile) => Promise<void>)
		| null = null;
	export let onDraftPrompt: ((text: string) => void) | null = null;
	export let stopResponse: Function = () => {};
	export let showMessage: Function = () => {};
	export let files: any[] = [];
	export let modelId: string | null = null;
	export let systemPrompt = '';
	export let canOpenChatTab = false;
	$: canOpenChat = $user?.role === 'admin' || $user?.role === 'user';

	export let codeInterpreterEnabled = false;
	// Retired layout controls: keep their translations.
	// $i18n.t('Use full-width tabs')
	// $i18n.t('Use side tabs')
	export let fullWidth = false;
	export let mainChatActive = false;
	export let mainChatStyle = '';
	export let mainChatGroupId = '';
	let paneCanvas: HTMLDivElement;
	export let title = '';
	export let mainTabFolder: {
		id: string;
		name: string;
		icon?: string | null;
		canEdit?: boolean;
	} | null = null;
	/** Double-clicking the folder tab renames the folder inline. */
	export let onRenameFolder: ((folderId: string, name: string) => Promise<void>) | null = null;
	let isRenamingFolder = false;
	let folderNameDraft = '';
	const startFolderRename = async () => {
		if (!mainTabFolder?.canEdit || !onRenameFolder) return;
		folderNameDraft = mainTabFolder.name;
		isRenamingFolder = true;
		await tick();
		const input = document.querySelector<HTMLInputElement>('[data-folder-tab-rename]');
		input?.focus();
		input?.select();
	};
	const saveFolderRename = async () => {
		if (!isRenamingFolder || !mainTabFolder) return;
		isRenamingFolder = false;
		const name = folderNameDraft.trim();
		if (name && name !== mainTabFolder.name) await onRenameFolder?.(mainTabFolder.id, name);
	};
	$: if (!mainTabFolder) isRenamingFolder = false;
	$: mainTabTitle = mainTabFolder?.name ?? title;
	/** What the open tabs belong to: the folder on screen, or the chat. */
	$: panelChatId = mainTabFolder && $user ? folderSessionId(mainTabFolder.id, $user.id) : chatId;
	export let getEmbeddedDraft: (
		text?: string,
		files?: any[]
	) => NonNullable<ComponentProps<Chat>['embeddedDraft']>;
	$: if (
		viewReady &&
		!chatLoading &&
		isPanelViewReady(panelChatId, viewEntry) &&
		$chatTabRequest &&
		'folderId' in $chatTabRequest &&
		$chatTabRequest.folderId === mainTabFolder?.id
	) {
		chatTabRequest.set(null);
		if (mainTabFolder?.canEdit) openFeatureTab('chat');
	}
	export let mainChatHref = '/';
	export let tabTitleEditor: import('svelte').Snippet | undefined = undefined;
	/** Double-clicking the main chat tab renames the chat. */
	export let onRenameMainTab: (() => void) | null = null;
	export let tabActions: import('svelte').Snippet | undefined = undefined;
	export let tabBarActions: import('svelte').Snippet | undefined = undefined;
	$: fullWidth = isLargeScreen;
	$: panelVisible = isLargeScreen || !!$showTabs;

	let isLargeScreen = false;
	let isDragging = false;
	let isMounted = false;
	let viewportWidth = 0;

	let tabs = createTabsState();
	const toPaneStyle = (rect: GroupRect, header = 0) =>
		`position:absolute;left:${rect.left * 100}%;top:calc(100% * ${rect.top} + ${header}px * var(--app-text-scale, 1));width:${rect.width * 100}%;height:calc(100% * ${rect.height} - ${header}px * var(--app-text-scale, 1));`;
	const focusGroup = (id: string, event?: Event) => {
		// Tab clicks activate their own group.
		if (event?.target instanceof Element && event.target.closest('[data-panel-tab]')) return;
		const group = tabs.groups.find((group) => group.id === id);
		if (group?.activeId && tabs.activeGroupId !== id) tabs = activateTab(tabs, group.activeId);
	};
	let terminalViews: Record<string, XTerminal> = {};
	let terminalTitles: Record<string, string> = {};
	let terminalProcesses: Record<string, string> = {};
	export const hasTerminalTabs = () => tabs.tabs.some((tab) => tab.kind === 'terminal');
	let browserViews: Record<string, Browser> = {};
	let gitViews: Record<string, GitBar> = {};
	let chatViews: Record<string, ChatTab> = {};
	let chatTitleEditors: Record<string, import('svelte').Snippet | undefined> = {};
	let chatTabActions: Record<string, import('svelte').Snippet | undefined> = {};
	let chatStreamingStates: Record<string, boolean> = {};
	// Each chat writes its artifacts here; its artifacts tab reads them.
	const chatArtifacts: Record<string, Writable<{ type: string; content: string }[]>> = {};
	const getChatArtifacts = (id: string) => (chatArtifacts[id] ??= writable([]));
	const getArtifactsStore = (sourceTabId = mainChatTabId) =>
		sourceTabId === mainChatTabId ? mainArtifacts : getChatArtifacts(sourceTabId);
	// The code block each artifacts tab was last asked to show.
	let artifactSelections: Record<string, { code: string }> = {};
	let queuedArtifactCode: { code?: string } | null = null;
	type ChatViewEntry = ReturnType<typeof chatViewEntry>;
	/**
	 * Where the tab layout of the current chat stands.
	 * - idle: nothing is shown (before the first load, after a chat switch or sign-out)
	 * - loading / loadFailed: the layout saved for `chatId` is being read, or could not be
	 * - ready: the layout of `chatId` is shown; `error` reports a failed save
	 * - carrying: a new chat kept the open pages and waits for `chatId` to move off `fromChatId`
	 * - attaching / attachFailed: an unsaved layout is being moved to the chat `chatId`
	 */
	type ViewState =
		| { status: 'idle' }
		| { status: 'loading'; entry: ChatViewEntry; chatId: string | null }
		| { status: 'loadFailed'; entry: ChatViewEntry; chatId: string | null; error: string }
		| { status: 'ready'; entry: ChatViewEntry; chatId: string | null; error: string }
		| { status: 'carrying'; entry: ChatViewEntry; fromChatId: string | null }
		| { status: 'attaching'; entry: ChatViewEntry; chatId: string; done: Promise<void> }
		| { status: 'attachFailed'; entry: ChatViewEntry; chatId: string; error: string };
	let viewState: ViewState = { status: 'idle' };
	// Read-only projections of `viewState`; only setView writes them.
	let viewEntry: ChatViewEntry | null = null;
	let viewReady = false;
	let viewError = '';
	const setView = (next: ViewState) => {
		viewState = next;
		viewEntry = next.status === 'idle' ? null : next.entry;
		viewReady = ['ready', 'carrying', 'attaching', 'attachFailed'].includes(next.status);
		viewError = 'error' in next ? next.error : '';
	};
	let sessionFailures: Record<string, { message: string; status?: number }> = {};
	let sessionAttempts: Record<string, number> = {};

	export function captureView() {
		if (!viewEntry || !viewReady) return;
		const chatView = viewEntry;
		for (const tab of tabs.tabs) {
			const draft = fileViews[tab.id]?.captureView?.();
			if (draft) chatView.drafts.set(tab.id, draft);
			if (gitViews[tab.id]) chatView.transient[`git:${tab.id}`] = gitViews[tab.id].captureView();
			if (chatViews[tab.id]) chatView.transient[`chat:${tab.id}`] = chatViews[tab.id].captureView();
		}
		chatView.transient.gitDiffModes = fileGitDiffModes;
		chatView.transient.gitHideWhitespace = fileGitHideWhitespace;
		const snapshot = {
			...tabs,
			tabs: tabs.tabs.map((tab) => ({
				...tab,
				...(tab.kind === 'files' && chatView.drafts.get(tab.id)?.directory
					? { directory: chatView.drafts.get(tab.id).directory }
					: {})
			}))
		};
		changeChatView(chatView, {
			...chatView.state,
			panels: snapshot,
			selectedMachineId: $selectedMachineId
		});
	}
	const leaveChatView = () => {
		stopTerminalChoice?.(false);
		stopTerminalChoice = null;
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
	};
	export function resetForChatSwitch() {
		leaveChatView();
		setView({ status: 'idle' });
		tabs = createTabsState();
		chatStreamingStates = {};
		chatTitleEditors = {};
		chatTabActions = {};
		queuedArtifactCode = null;
	}
	/** Starts a new chat that keeps the open pages; everything else stays with the chat being left. */
	export function carryPagesToNewChat() {
		if (!viewReady || !$user?.id) return resetForChatSwitch();
		leaveChatView();
		let carried = tabs;
		for (const tab of tabs.tabs) {
			if (tab.id !== mainChatTabId && tab.kind !== 'page') carried = removeTab(carried, tab.id);
		}
		const kept = new Set(carried.tabs.map((tab) => tab.id));
		const keep = <T,>(record: Record<string, T>) =>
			Object.fromEntries(Object.entries(record).filter(([id]) => kept.has(id)));
		dirtyFiles = keep(dirtyFiles);
		fileContexts = keep(fileContexts);
		chatStreamingStates = {};
		chatTitleEditors = {};
		chatTabActions = {};
		queuedArtifactCode = null;
		const entry = chatViewEntry($user.id, null, $temporaryChat);
		entry.state = {
			...entry.state,
			panels: carried,
			selectedMachineId: $selectedMachineId
		};
		setView({ status: 'carrying', entry, fromChatId: panelChatId });
		tabs = carried;
		hasExtraTabs = carried.tabs.some((tab) => tab.id !== mainChatTabId);
	}
	export function attachChatViewTo(id: string): Promise<void> {
		if (viewState.status === 'attaching') return viewState.done;
		if (
			viewState.status !== 'ready' &&
			viewState.status !== 'carrying' &&
			viewState.status !== 'attachFailed'
		)
			return Promise.resolve();
		const entry = viewState.entry;
		if (entry.chatId === id) return Promise.resolve();
		captureView();
		const done = promoteChatView(
			entry,
			id,
			async () => {
				await tick();
				for (const tab of entry.state.panels.tabs) {
					if (!tab.sessionId) continue;
					if (tab.kind === 'terminal') {
						if (!terminalViews[tab.id]) throw new Error('Terminal is not connected');
						await terminalViews[tab.id].bindChat(id);
					} else if (tab.kind === 'browser') {
						if (!browserViews[tab.id]) throw new Error('Browser is not connected');
						await browserViews[tab.id].bindChat(id);
					}
				}
			},
			$temporaryChat
		).then(
			() => {
				if (viewEntry === entry) setView({ status: 'ready', entry, chatId: id, error: '' });
			},
			(error) => {
				if (viewEntry === entry)
					setView({
						status: 'attachFailed',
						entry,
						chatId: id,
						error: entry.error || String(error)
					});
				throw error;
			}
		);
		setView({ status: 'attaching', entry, chatId: id, done });
		return done;
	}

	let lastFolderView: string | null = null;
	async function restoreChatView(id: string | null) {
		if (!$user?.id) return;
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		// A chat shows while its layout loads. A folder opens as it was left, so it waits.
		tabs = isFolderSessionId(id)
			? createTabsState()
			: setMainChatTab(createTabsState(), true, mainTabTitle);
		terminalTitles = {};
		terminalProcesses = {};
		chatStreamingStates = {};
		chatTitleEditors = {};
		chatTabActions = {};
		const entry = chatViewEntry($user.id, id, $temporaryChat);
		const loading: ViewState = { status: 'loading', entry, chatId: id };
		setView(loading);
		try {
			await loadChatView(entry);
			if (viewState !== loading) return;
			// The chat restores its machine and directory together; layouts must not override them.
			entry.state.selectedMachineId = $selectedMachineId;
			let panels = setMainChatTab(entry.state.panels, true, mainTabTitle);
			const mainGroup = panels.groups.find((group) => group.tabIds.includes(mainChatTabId));
			const activeIds = [panels.activeId, mainGroup?.activeId];
			// Opening a chat shows that chat, not the page or other chat it was left on. A folder opens
			// as it was left; opening it again from inside shows the folder itself.
			if (isFolderSessionId(id)) {
				if (id === lastFolderView && !pendingPageTab) panels = activateTab(panels, mainChatTabId);
			} else if (
				panels.tabs.some(
					(tab) =>
						activeIds.includes(tab.id) &&
						tab.id !== mainChatTabId &&
						(tab.kind === 'page' || tab.kind === 'chat')
				)
			)
				panels = activateTab(panels, mainChatTabId);
			entry.state.panels = panels;
			tabs = entry.state.panels;
			dirtyFiles = {};
			fileContexts = {};
			fileGitStatuses = {};
			fileGitDiffModes = entry.transient.gitDiffModes ?? {};
			fileGitHideWhitespace = entry.transient.gitHideWhitespace ?? {};
			commentAnchor = {};
			sessionFailures = {};
			sessionAttempts = {};
			lastFolderView = isFolderSessionId(id) ? id : null;
			setView({ status: 'ready', entry, chatId: id, error: entry.error });
			if (isFolderSessionId(id) && !entry.persisted && machineIdOf($selectedFolder?.data))
				openFiles($selectedMachineId, $selectedFolder?.data?.working_directory || undefined);
			hasExtraTabs = tabs.tabs.some((tab) => tab.id !== mainChatTabId);
		} catch (error) {
			if (viewState === loading)
				setView({ status: 'loadFailed', entry, chatId: id, error: String(error) });
		}
	}
	/** Keeps the layout in step with the chat: carry it over, attach it to the new chat id, or load. */
	function followChat(current: ViewState, id: string | null) {
		if (current.status === 'idle') return void restoreChatView(id);
		// A folder keeps its own tabs; nothing is carried into it.
		if (isFolderSessionId(id) && current.entry.chatId !== id) return void restoreChatView(id);
		if (current.status === 'carrying') {
			if (id === current.fromChatId) return;
			if (id) void attachChatViewTo(id).catch(() => {});
			else setView({ status: 'ready', entry: current.entry, chatId: id, error: '' });
			return;
		}
		if (current.chatId === id) return;
		const unsaved = !current.entry.chatId;
		if (unsaved && id && (current.status === 'ready' || current.status === 'attachFailed'))
			void attachChatViewTo(id).catch(() => {});
		else void restoreChatView(id);
	}
	const persistPanels = (nextTabs: typeof tabs, machineId: string | null, ready: boolean) => {
		if (!ready || !viewEntry || chatLoading || viewEntry.promoting) return;
		// The Files tab follows the machine picked for the chat and starts over there.
		if (machineId && machineId !== viewEntry.state.selectedMachineId) {
			const moved = nextTabs.tabs.filter(
				(tab) => tab.kind === 'files' && tab.machineId !== machineId
			);
			for (const tab of moved) {
				viewEntry.drafts.delete(tab.id);
				delete fileContexts[tab.id];
			}
			nextTabs = {
				...nextTabs,
				tabs: nextTabs.tabs.map((tab) =>
					moved.includes(tab)
						? {
								...tab,
								label: $i18n.t('Files'),
								machineId: machineId,
								target: undefined,
								path: undefined,
								directory: undefined
							}
						: tab
				)
			};
		}
		if (viewEntry.state.panels !== nextTabs || viewEntry.state.selectedMachineId !== machineId)
			changeChatView(viewEntry, {
				...viewEntry.state,
				panels: nextTabs,
				selectedMachineId: machineId
			});
	};
	$: persistPanels(tabs, $selectedMachineId, viewReady);
	$: if (viewEntry && viewEntry.userId !== $user?.id) {
		setView({ status: 'idle' });
		tabs = createTabsState();
		chatStreamingStates = {};
		chatTitleEditors = {};
		chatTabActions = {};
		clearChatViews();
	}
	const forgetDraftsForUnreachableMachines = (..._connections: unknown[]) => {
		captureView();
		// A returning component must read disk before restoring its cached draft.
		for (const tab of tabs.tabs) {
			if (tab.machineId && !isMachineReachable(tab.machineId)) delete dirtyFiles[tab.id];
		}
		dirtyFiles = { ...dirtyFiles };
	};
	$: if (isMounted && viewReady)
		forgetDraftsForUnreachableMachines($machines, $settings, $config, $user);
	const resolveTabConnection = (tab: Tab) => {
		if (!tab.machineId || !isMachineReachable(tab.machineId)) return null;
		const target = resolveMachineTarget(
			tab.machineId,
			$machines ?? [],
			localStorage.token ?? '',
			tab.target?.context ?? {
				// A session that came along with a chat stays under that chat.
				chatId: (tab.kind !== 'chat' && tab.chatId) || panelChatId,
				modelId: modelId ?? null
			}
		);
		if (target) tab.target = target;
		return target;
	};
	const startSession = (chatView: NonNullable<typeof viewEntry>, tab: Tab) => {
		const target = resolveTabConnection(tab);
		if (target) {
			delete sessionFailures[tab.id];
			void createViewSession(
				chatView,
				tab.id,
				target,
				getCurrentDirectory(target.selector) ||
					(machineIdOf($selectedFolder?.data) === target.selector
						? $selectedFolder?.data?.working_directory || undefined
						: undefined)
			);
		}
	};
	const stopSession = (target: MachineTarget, kind: Tab['kind'], sessionId: string) =>
		machineRequest(
			target,
			`${kind === 'terminal' ? '/api/terminals' : '/browser/sessions'}/${encodeURIComponent(sessionId)}`,
			{ method: 'DELETE' }
		);
	/** Points a tab at the chat model's instance, on machines with an instance per model. */
	const updateTabTarget = async (chatView: ChatViewEntry, id: string) => {
		// A session that is still starting can only be stopped once it has started.
		await chatView.pending.get(id);
		if (chatView !== viewEntry || !modelId) return;
		const tab = chatView.state.panels.tabs.find((tab) => tab.id === id);
		const previousTarget = tab?.target;
		if (!tab || !previousTarget?.context.modelId || previousTarget.context.modelId === modelId)
			return;
		// Unsaved edits stay on the instance their file was opened from.
		if (dirtyFiles[id] ?? chatView.drafts.get(id)?.dirty) return;
		const nextTab = {
			...tab,
			target: { ...previousTarget, context: { ...previousTarget.context, modelId } },
			sessionId: undefined
		};
		updateViewTab(chatView, id, nextTab);
		if (tab.sessionId) {
			void stopSession(previousTarget, tab.kind, tab.sessionId).catch(() => {});
			startSession(chatView, nextTab);
		}
	};
	$: if (viewReady && !chatLoading && modelId) {
		for (const tab of viewEntry?.state.panels.tabs ?? []) void updateTabTarget(viewEntry!, tab.id);
	}

	let fileViews: Record<
		string,
		{
			hasUnsavedChanges: () => boolean;
			requestClose: () => Promise<boolean>;
			browseDirectory?: (path: string) => unknown;
			refreshDirectory?: () => unknown;
			revealPage?: (page: number | null) => void;
			captureView?: () => any;
		}
	> = {};
	let dirtyFiles: Record<string, boolean> = {};
	let fileContexts: Record<string, MachineContext | null> = {};
	let panelTarget: HTMLElement | null = null;
	let hasExtraTabs = false;
	let commentAnchor: { comment_id?: string } = {};
	let closingTabIds = new Set<string>();
	let selectedConnection: MachineTarget | null = null;
	let showQuickOpen = false;
	let voiceNote: VoiceNote;
	let voiceNoteDestination: {
		target: MachineTarget;
		chatId: string | null;
		directory?: string;
	} | null = null;
	$: canVoiceNote = supportsMachineFiles && !!$user;
	$: canTranscribeVoiceNote = $user?.role === 'admin' || ($user?.permissions?.chat?.stt ?? true);
	const openVoiceNote = () => {
		if (voiceNoteDestination) {
			voiceNote?.finishRecording();
			return;
		}
		if (!selectedConnection) return askForMachine(openVoiceNote);
		if (!canVoiceNote || !$user) return;
		voiceNoteDestination = {
			target: selectedConnection,
			chatId: panelChatId,
			directory: getCurrentDirectory(selectedConnection.selector)
		};
	};
	$: if (!supportsMachineFiles) showQuickOpen = false;
	let supportsMachine = false;
	let supportsDesktop = false;
	let supportsBrowser = false;
	let featureCheckRequestId = 0;
	let releasePanel: (target: HTMLElement) => void = () => {};
	const preservePanel = (target: HTMLElement) => ({ destroy: () => releasePanel(target) });

	// Move a single mounted panel between desktop, mobile, and its hidden parking spot.
	const placePanel = (node: HTMLElement, target: HTMLElement | null) => {
		const home = node.parentElement!;
		const move = (destination: HTMLElement | null) => {
			const parent = (destination ?? home) as HTMLElement & {
				moveBefore?: (node: Node, before: Node | null) => void;
			};
			if (node.parentElement === parent) return;
			if (parent.moveBefore && node.isConnected && parent.isConnected)
				parent.moveBefore(node, null);
			else parent.appendChild(node);
		};
		releasePanel = (target) => {
			if (node.parentElement === target) move(null);
		};
		const update = (destination: HTMLElement | null) => {
			if (!destination) {
				move(null);
				return;
			}
			// Wait until the drawer has attached its destination to the document.
			void tick().then(() => {
				if (panelVisible && panelTarget === destination && destination.isConnected)
					move(destination);
			});
		};
		update(target);
		return { update, destroy: () => node.remove() };
	};
	const pageIcons: Record<string, typeof NotesIcon> = {
		notes: NotesIcon,
		workspace: WorkspaceIcon,
		automations: ClockIcon,
		calendar: CalendarIcon,
		playground: CodeIcon,
		home: HomeIcon,
		channels: HashtagIcon
	};
	const getTabIcon = (kind: Tab['kind']) =>
		({
			chat: 'chat-lines',
			page: 'page',
			files: 'folder',
			file: 'page',
			terminal: 'terminal',
			browser: 'browser',
			desktop: 'monitor',
			artifacts: 'code',
			preview: 'browser',
			voice: 'microphone',
			comments: 'chat-bubble',
			overview: 'grid'
		})[kind];
	const toTabDomId = (id: string) => `chat-panel-${encodeURIComponent(id)}`;
	$: activeTabId = tabs.activeId;
	$: activeTab = tabs.tabs.find((tab) => tab.id === tabs.activeId);
	$: contextTab =
		activeTab?.id === mainChatTabId
			? tabs.tabs.find((tab) => tab.id === tabs.history.at(-1))
			: activeTab;
	$: activeFileContext = (contextTab && fileContexts[contextTab.id]) ?? contextTab?.context ?? null;
	/** The folder the active file panel shows on `machineId`, if it shows one there. */
	export const getCurrentDirectory = (machineId: string | null) =>
		activeFileContext?.machineId === machineId ? activeFileContext.currentDirectory : undefined;
	$: if (activeTabId && panelTarget) {
		const id = activeTabId;
		void tick().then(() =>
			document
				.getElementById(toTabDomId(id))
				?.parentElement?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
		);
	}

	export const focusMainChat = () => {
		tabs = activateTab(tabs, mainChatTabId);
	};
	const selectTab = (id: string) => {
		tabs = activateTab(tabs, id);
		showTabs.set(true);
	};
	const activateFilesOnDrag = (node: HTMLElement, tab: Tab) => {
		if (tab.kind !== 'files') return;
		let timer: ReturnType<typeof setTimeout> | undefined;
		const clear = () => {
			clearTimeout(timer);
			timer = undefined;
		};
		const over = (event: DragEvent) => {
			if (!event.dataTransfer?.types.includes('application/x-machine-file-move') || timer) return;
			if (tabs.groups.some((group) => group.activeId === tab.id)) return;
			timer = setTimeout(() => {
				selectTab(tab.id);
				clear();
			}, 500);
		};
		const leave = (event: DragEvent) => {
			if (!(event.relatedTarget instanceof Node && node.contains(event.relatedTarget))) clear();
		};
		node.addEventListener('dragover', over);
		node.addEventListener('dragleave', leave);
		node.addEventListener('drop', clear);
		window.addEventListener('dragend', clear);
		return {
			destroy() {
				clear();
				node.removeEventListener('dragover', over);
				node.removeEventListener('dragleave', leave);
				node.removeEventListener('drop', clear);
				window.removeEventListener('dragend', clear);
			}
		};
	};
	const openPanel = (tab: Tab, inSplit = false, besideId?: string) => {
		if (!viewReady || !viewEntry) return;
		hasExtraTabs = true;
		if (tab.machineId) {
			const target =
				tab.target ??
				resolveMachineTarget(tab.machineId, $machines ?? [], localStorage.token, {
					chatId: panelChatId,
					modelId: modelId ?? null
				});
			tab = { ...tab, target: target ?? undefined };
		}
		tabs = inSplit ? openTabInSplit(tabs, tab, besideId) : openTab(tabs, tab);
		changeChatView(viewEntry, { ...viewEntry.state, panels: tabs });
		showTabs.set(true);
	};
	const createPageTab = (request: { href: string; label: string }): Tab => {
		const url = new URL(request.href, location.origin);
		const chat = url.pathname === '/' || url.pathname.startsWith('/c/');
		return {
			id: `${chat ? 'chat' : 'page'}:${uuidv4()}`,
			kind: chat ? 'chat' : 'page',
			href: url.pathname + url.search + url.hash,
			chatId: url.pathname.startsWith('/c/')
				? decodeURIComponent(url.pathname.slice(3))
				: undefined,
			initialPrompt: chat ? (url.searchParams.get('q') ?? '') : undefined,
			label: request.label || $i18n.t(chat ? 'Chat' : 'Loading...')
		};
	};
	const findPageTab = (url: URL) =>
		tabs.tabs.find(
			(tab) =>
				(tab.href && pageTabKey(new URL(tab.href, location.origin)) === pageTabKey(url)) ||
				(tab.kind === 'chat' && tab.chatId && url.pathname === `/c/${tab.chatId}`) ||
				(url.pathname === '/workspace' && tab.href?.startsWith('/workspace/'))
		);
	// A folder's tabs are not there yet while the chat being left is still shown.
	const isPanelViewReady = (id: string | null, entry: ChatViewEntry | null) =>
		!isFolderSessionId(id) || entry?.chatId === id;
	export const openPageTab = (request: { href: string; label: string; inSplit?: boolean }) => {
		const url = new URL(request.href, location.origin);
		if (url.origin !== location.origin || !pageTabKey(url)) return;
		if (!viewReady || !isPanelViewReady(panelChatId, viewEntry)) {
			pendingPageTab = request;
			return;
		}
		if ((url.pathname === '/' && !url.search) || request.href === mainChatHref) {
			focusMainChat();
			return;
		}
		const existing = findPageTab(url);
		if (existing) {
			selectTab(existing.id);
			if (
				existing.kind === 'page' &&
				existing.href !== request.href &&
				url.pathname !== '/workspace'
			)
				void navigatePageTab(existing.id, request.href);
		} else openPanel(createPageTab(request), request.inSplit);
	};
	/** Brings the live shells and browsers of a chat into its folder's tabs. */
	export const joinChatSessions = async (id: string) => {
		const saved = await getChatView(id).catch(() => null);
		const entry = viewEntry;
		if (!entry || !isFolderSessionId(panelChatId) || entry.chatId !== panelChatId) return;
		for (const tab of saved?.state?.panels.tabs ?? []) {
			if (!tab.sessionId || !tab.machineId || !['terminal', 'browser'].includes(tab.kind)) continue;
			const joined = { ...tab, chatId: id };
			const target = resolveTabConnection(joined);
			const path = tab.kind === 'terminal' ? '/api/terminals' : '/browser/sessions';
			const alive =
				target &&
				(await machineRequest(target, `${path}/${encodeURIComponent(tab.sessionId)}`).then(
					() => true,
					() => false
				));
			if (!alive || entry !== viewEntry || !viewReady) continue;
			if (tabs.tabs.some((item) => item.id === tab.id)) continue;
			const activeId = tabs.activeId;
			tabs = activateTab(openTab(tabs, joined), activeId);
		}
	};
	const navigatePageTab = async (id: string, href: string) => {
		const url = new URL(href, location.origin);
		if (url.pathname === '/' && !url.search) {
			await closeTab(id);
			focusMainChat();
			return;
		}
		const existing = findPageTab(url);
		if (existing?.kind === 'page' && existing.id !== id) {
			await closeTab(id);
			if (!tabs.tabs.some((tab) => tab.id === id)) openPageTab({ href, label: '' });
			return;
		}
		if (!((await pageViews[id]?.requestClose()) ?? true)) return;
		if (url.pathname === '/' || url.pathname.startsWith('/c/')) {
			openPageTab({ href, label: '' });
		} else if (viewEntry) updateViewTab(viewEntry, id, { href });
		await tick();
	};

	$: if (viewReady && pendingPageTab && isPanelViewReady(panelChatId, viewEntry)) {
		const request = pendingPageTab;
		pendingPageTab = null;
		// Once the restored tabs are in place, so they cannot overwrite the choice.
		void tick().then(() => openPageTab(request));
	}
	$: if (viewReady && chatId) {
		const duplicate = tabs.tabs.find(
			(tab) => tab.kind === 'chat' && tab.id !== mainChatTabId && tab.chatId === chatId
		);
		if (duplicate) void closeTab(duplicate.id);
	}

	const openFiles = (
		machineId = $selectedMachineId,
		directory?: string,
		newTab = false,
		sourceModelId = modelId
	) => {
		if (!machineId && !showFilesTab)
			return askForMachine(() => openFiles($selectedMachineId, directory, newTab, sourceModelId));
		if (machineId ? !isMachineReachable(machineId) : !showFilesTab) return;
		const target = resolveMachineTarget(machineId, $machines ?? [], localStorage.token, {
			chatId: panelChatId,
			modelId: sourceModelId ?? null
		});
		const pinnedModel = target?.context.modelId ?? null;
		const existing = newTab
			? undefined
			: (tabs.tabs.find(
					(tab) =>
						tab.id === tabs.activeId &&
						tab.kind === 'files' &&
						(tab.machineId ?? null) === machineId &&
						(tab.target?.context.modelId ?? null) === pinnedModel
				) ??
				tabs.tabs.find(
					(tab) =>
						tab.kind === 'files' &&
						(tab.machineId ?? null) === machineId &&
						(tab.target?.context.modelId ?? null) === pinnedModel
				));
		if (!existing && machineContext?.machineId === machineId)
			directory ??= machineContext.currentDirectory || undefined;
		const id = existing?.id ?? uuidv4();
		openPanel({
			id,
			kind: 'files',
			label: $i18n.t('Files'),
			machineId: machineId ?? undefined,
			target: target ?? undefined,
			path: directory
		});
		const view = fileViews[id];
		if (
			directory &&
			view &&
			view.captureView()?.directory?.replace(/\/+$/, '') !== directory.replace(/\/+$/, '')
		)
			void view.browseDirectory(directory);
	};
	const openFile = (
		path: string,
		machineId: string,
		page?: number | null,
		sourceModelId = modelId
	) => {
		if (!isMachineReachable(machineId)) return;
		const target = resolveMachineTarget(machineId, $machines ?? [], localStorage.token, {
			chatId: panelChatId,
			modelId: sourceModelId ?? null
		});
		const pinnedModel = target?.context.modelId ?? null;
		path = path.replace(/\\/g, '/').replace(/\/{2,}/g, '/');
		const id =
			tabs.tabs.find(
				(tab) =>
					tab.kind === 'file' &&
					!tab.untitled &&
					tab.machineId === machineId &&
					(tab.target?.context.modelId ?? null) === pinnedModel &&
					tab.path === path
			)?.id ?? fileTabId(JSON.stringify([machineId, pinnedModel]), path);
		openPanel({
			id,
			kind: 'file',
			label: path.split('/').pop() || path,
			machineId: machineId,
			target: target ?? undefined,
			path,
			page
		});
		if (page != null) fileViews[id]?.revealPage?.(page);
	};
	const openNewFileTab = () => {
		if (!selectedConnection) return askForMachine(openNewFileTab);
		let number = 1;
		while (tabs.tabs.some((tab) => tab.untitled && tab.label === `Untitled-${number}`)) number++;
		openPanel({
			id: uuidv4(),
			kind: 'file',
			label: `Untitled-${number}`,
			machineId: selectedConnection.selector,
			target: { ...selectedConnection },
			untitled: true,
			context:
				activeFileContext?.machineId === selectedConnection.selector ? activeFileContext : undefined
		});
	};
	/** Opens the artifacts tab of the chat in `sourceTabId` beside that chat. */
	export const openArtifacts = (code?: string, sourceTabId = mainChatTabId, inSplit = true) => {
		if (!$visibleControls['chat.artifacts']) return;
		if (sourceTabId === mainChatTabId && !viewReady) {
			// the chat's messages can render before its tabs are restored
			queuedArtifactCode = { code };
			return;
		}
		if (!get(getArtifactsStore(sourceTabId)).length) return;
		const id = `artifacts:${sourceTabId}`;
		if (code) artifactSelections = { ...artifactSelections, [id]: { code } };
		openPanel(
			{ id, kind: 'artifacts', label: $i18n.t('Artifacts'), sourceTabId },
			inSplit,
			sourceTabId
		);
	};
	const openOverview = (sourceTabId = mainChatTabId) => {
		if (sourceTabId === mainChatTabId) {
			if (!hasMessages) return;
			openPanel({ id: 'overview', kind: 'overview', label: $i18n.t('Overview') });
			return;
		}
		openPanel({
			id: `overview:${sourceTabId}`,
			kind: 'overview',
			label: $i18n.t('Overview'),
			sourceTabId
		});
	};
	$: if (viewReady && queuedArtifactCode) {
		const { code } = queuedArtifactCode;
		queuedArtifactCode = null;
		openArtifacts(code);
	}
	export const openFeatureTab = (
		kind: 'artifacts' | 'preview' | 'voice' | 'comments' | 'chat',
		inSplit = false,
		text?: string,
		files?: any[]
	) => {
		if (!availableViews.some((view) => view.kind === kind && view.available)) return;
		if (kind === 'artifacts') return openArtifacts(undefined, mainChatTabId, inSplit);
		if (kind === 'preview') return openPreview();
		const view = availableViews.find((view) => view.kind === kind)!;
		if (kind === 'chat') {
			if (!viewReady || !viewEntry) return false;
			const id = uuidv4();
			if (mainTabFolder?.canEdit) {
				viewEntry.transient[`chat:${id}`] = { embeddedDraft: getEmbeddedDraft(text, files) };
			}
			let chatNumber = 1;
			while (tabs.tabs.some((tab) => tab.kind === 'chat' && tab.chatNumber === chatNumber))
				chatNumber++;
			const pending = $chatTabRequest && 'parentChatId' in $chatTabRequest ? $chatTabRequest : null;
			const initialPrompt = pending?.parentChatId === chatId ? pending.prompt : '';
			if (pending?.parentChatId === chatId) chatTabRequest.set(null);
			openPanel(
				{
					id,
					kind,
					label: `${view.label} ${chatNumber}`,
					chatNumber,
					parentChatId: pending?.parentChatId === chatId ? (chatId ?? undefined) : undefined,
					initialPrompt
				},
				inSplit
			);
			return true;
		}
		openPanel({ id: kind, kind, label: view.label }, inSplit);
	};
	const openPreview = () => {
		const sourceTabId = embedSourceTab?.id;
		const sourceGroup = tabs.groups.find((group) => group.tabIds.some((id) => id === sourceTabId));
		// Each cited source has its own tab; citing it again shows the new passages there.
		const id = `preview:${$embed.file?.id ?? $embed.key ?? $embed.url}`;
		tabs = {
			...tabs,
			tabs: tabs.tabs.map((tab) => (tab.id === id ? { ...tab, embed: $embed } : tab))
		};
		// A source cited in the main chat opens beside it, so the answer stays readable.
		openPanel({ id, kind: 'preview', label: $i18n.t('Preview'), embed: $embed }, !sourceGroup);
		// A source cited in a chat tab opens in that tab's group, so the main chat stays in view.
		if (sourceGroup) tabs = moveTabToGroup(tabs, id, sourceGroup.id);
	};

	type SplitDrop = GroupRect & { groupId: string; edge: SplitEdge | null };
	let chatDropPreview: SplitDrop | null = null;
	let draggedTabId = '';
	let pendingTabDrop: (() => void) | null = null;
	const clearChatDropPreview = () => (chatDropPreview = null);
	const canDropChat = (event: Pick<DragEvent, 'dataTransfer'>) =>
		canOpenChat &&
		($user?.role === 'admin' ||
			!(
				($user?.permissions?.chat?.temporary ?? true) &&
				($user?.permissions?.chat?.temporary_enforced ?? false)
			)) &&
		event.dataTransfer?.types.includes('application/x-open-webui-chat');
	const getChatDropZone = (
		event: Pick<DragEvent, 'target' | 'clientX' | 'clientY' | 'dataTransfer'>
	): SplitDrop | null => {
		const internal =
			!!draggedTabId || event.dataTransfer?.types.includes('application/x-chat-panel-tab');
		if (
			(!internal &&
				!canDropChat(event) &&
				!event.dataTransfer?.types.includes('application/x-open-webui-page')) ||
			!(event.target instanceof Element)
		)
			return null;
		if (!internal && event.target.closest('[data-composer-id]')) return null;
		const group = event.target.closest<HTMLElement>('[data-panel-group]');
		const panel = event.target.closest('#controls-container');
		const main = !group && !panel;
		const element =
			group ??
			panel ??
			event.target.closest('[data-main-chat-pane]') ??
			event.target.closest('#chat-container');
		const rect = element?.getBoundingClientRect();
		if (!rect?.width || !rect.height) return null;
		const groupId = group?.dataset.panelGroup ?? tabs.activeGroupId;
		const inTabBar = !!event.target.closest('[data-panel-tab-bar]');
		const edges: { edge: SplitEdge; distance: number }[] = [];
		if (fullWidth && !inTabBar) {
			if (event.clientX - rect.left <= rect.width * 0.3)
				edges.push({ edge: 'left', distance: event.clientX - rect.left });
			if (rect.right - event.clientX <= rect.width * 0.3)
				edges.push({ edge: 'right', distance: rect.right - event.clientX });
			if (event.clientY - rect.top <= rect.height * 0.3)
				edges.push({ edge: 'top', distance: event.clientY - rect.top });
			if (rect.bottom - event.clientY <= rect.height * 0.3)
				edges.push({ edge: 'bottom', distance: rect.bottom - event.clientY });
		}
		const edge = edges.sort((a, b) => a.distance - b.distance)[0]?.edge ?? null;
		if (main && !edge) {
			if (!$showTabs && isLargeScreen) return null;
			if (internal || event.clientX < rect.right - rect.width * 0.3) return null;
			return {
				groupId: tabs.activeGroupId,
				edge: null,
				left: rect.left,
				top: rect.top,
				width: rect.width,
				height: rect.height
			};
		}
		const source = tabs.groups.find((item) => item.tabIds.includes(draggedTabId));
		if (internal && source?.id === groupId && (!edge || source.tabIds.length === 1)) return null;
		const width = edge === 'left' || edge === 'right' ? rect.width / 2 : rect.width;
		const height = edge === 'top' || edge === 'bottom' ? rect.height / 2 : rect.height;
		return {
			groupId,
			edge,
			width,
			height,
			left: rect.left + (edge === 'right' ? width : 0),
			top: rect.top + (edge === 'bottom' ? height : 0)
		};
	};
	export const handleChatDragOver = (event: DragEvent) => {
		chatDropPreview = getChatDropZone(event);
		if (chatDropPreview || event.dataTransfer?.types.includes('Files')) event.preventDefault();
		if (chatDropPreview)
			event.dataTransfer!.dropEffect =
				event.dataTransfer!.effectAllowed === 'move' ||
				event.dataTransfer!.types.includes('application/x-chat-panel-tab')
					? 'move'
					: 'copy';
	};
	export const handleChatDragLeave = (event: DragEvent) => {
		if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node))
			clearChatDropPreview();
	};
	export const handleChatDrop = (event: DragEvent) => {
		const bounds = getChatDropZone(event);
		clearChatDropPreview();
		if (
			event.dataTransfer?.types.includes('Files') &&
			!(
				event.target instanceof Element &&
				event.target.closest('[id="note-content-container"] [contenteditable="true"]')
			)
		)
			event.preventDefault();
		if (!bounds || pendingTabDrop) return;
		const internalId = event.dataTransfer?.getData('application/x-chat-panel-tab');
		let savedId = '';
		let droppedPage: Tab | null = null;
		if (internalId) {
			if (!tabs.tabs.some((tab) => tab.id === internalId)) return;
		} else if (event.dataTransfer?.types.includes('application/x-open-webui-page')) {
			try {
				const item = JSON.parse(event.dataTransfer.getData('application/x-open-webui-page'));
				if (typeof item.href !== 'string') return;
				const url = new URL(item.href, location.origin);
				if (url.origin !== location.origin || !pageTabKey(url)) return;
				droppedPage = createPageTab({
					href: url.pathname + url.search + url.hash,
					label: typeof item.label === 'string' ? item.label : ''
				});
			} catch {
				return;
			}
		} else {
			try {
				const item = JSON.parse(event.dataTransfer!.getData('text/plain'));
				if (item?.type !== 'chat' || typeof item.id !== 'string' || !item.id.trim()) return;
				savedId = item.id;
			} catch {
				return;
			}
		}
		event.preventDefault();
		const applyDrop = () => {
			const groupId = bounds.groupId;
			if (!droppedPage && savedId === chatId && !tabs.tabs.some((tab) => tab.id === mainChatTabId))
				return;
			const existing =
				internalId ||
				(droppedPage
					? findPageTab(new URL(droppedPage.href!, location.origin))?.id
					: savedId === chatId
						? mainChatTabId
						: tabs.tabs.find((tab) => tab.kind === 'chat' && tab.chatId === savedId)?.id);
			let id = existing;
			if (!id) {
				focusGroup(groupId);
				id = droppedPage?.id ?? uuidv4();
				tabs = openTab(
					tabs,
					droppedPage ?? { id, kind: 'chat', label: $i18n.t('Chat'), chatId: savedId }
				);
			}
			tabs = bounds.edge
				? splitTab(tabs, id, groupId, bounds.edge)
				: moveTabToGroup(tabs, id, groupId);
			showTabs.set(true);
		};
		if (internalId) {
			// Let Sortable restore its source DOM before changing the keyed tab groups.
			isTabDropHandled = true;
			pendingTabDrop = applyDrop;
		} else {
			event.stopPropagation();
			applyDrop();
		}
	};

	let resizingSplit: SplitDivider | null = null;
	const startSplitResize = (event: PointerEvent, divider: SplitDivider) => {
		event.preventDefault();
		resizingSplit = divider;
		isDragging = true;
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	};
	const moveSplitResize = (event: PointerEvent) => {
		if (!resizingSplit || !paneCanvas) return;
		const rect = paneCanvas.getBoundingClientRect();
		const split = resizingSplit;
		const ratio =
			split.direction === 'horizontal'
				? ((event.clientX - rect.left) / rect.width - split.left) / split.width
				: ((event.clientY - rect.top) / rect.height - split.top) / split.height;
		tabs = { ...tabs, layout: resizeSplit(tabs.layout, split.id, ratio) };
	};
	const endSplitResize = () => {
		resizingSplit = null;
		isDragging = false;
	};
	const openNewTerminalTab = () => {
		if (!selectedConnection) return askForMachine(openNewTerminalTab);
		let terminalNumber = 1;
		while (
			tabs.tabs.some((tab) => tab.kind === 'terminal' && tab.terminalNumber === terminalNumber)
		) {
			terminalNumber++;
		}
		const id = uuidv4();
		openPanel({
			id,
			kind: 'terminal',
			label: `${$i18n.t('Terminal')} ${terminalNumber}`,
			terminalNumber,
			machineId: selectedConnection.selector,
			target: { ...selectedConnection }
		});
		if (viewEntry && viewReady) startSession(viewEntry, tabs.tabs.find((tab) => tab.id === id)!);
	};
	const openDesktop = () => {
		if (!selectedConnection) return askForMachine(openDesktop);
		openPanel({
			id: JSON.stringify(['desktop', selectedConnection.baseUrl]),
			kind: 'desktop',
			label: $i18n.t('Desktop'),
			machineId: selectedConnection.selector,
			target: { ...selectedConnection }
		});
	};
	const getBrowserBaseUrl = (target: MachineTarget) => {
		const machine = ($machines ?? []).find((item) => item.id === target.selector);
		return chatContextNeedsSavedChat(machine) && target.context.chatId
			? `${target.baseUrl}/chats/${encodeURIComponent(target.context.chatId)}`
			: target.baseUrl;
	};
	const openBrowser = (
		port?: number,
		machineId = $selectedMachineId,
		baseUrl?: string,
		initialUrl?: string
	) => {
		if (!machineId)
			return askForMachine(() => openBrowser(port, $selectedMachineId, baseUrl, initialUrl));
		if (!isMachineReachable(machineId)) return;
		const url = initialUrl ?? (port ? `http://localhost:${port}/` : undefined);
		const existing =
			url &&
			tabs.tabs.find(
				(tab) =>
					tab.kind === 'browser' &&
					tab.machineId === machineId &&
					tab.path === url &&
					(tab.target?.context.modelId ?? null) === (selectedConnection?.context.modelId ?? null)
			);
		if (existing) {
			selectTab(existing.id);
			return;
		}
		const target = machineId
			? resolveMachineTarget(machineId, $machines ?? [], localStorage.token ?? '', {
					chatId: panelChatId,
					modelId: modelId ?? null
				})
			: null;
		if (!target) return;
		const machine = ($machines ?? []).find((item) => item.id === machineId);
		const proxyBase =
			baseUrl ??
			(target && chatContextNeedsSavedChat(machine) && panelChatId
				? `${target.baseUrl}/chats/${encodeURIComponent(panelChatId)}`
				: target?.baseUrl);
		const id = uuidv4();
		openPanel({
			id,
			kind: 'browser',
			label: port ? `localhost:${port}` : $i18n.t('Browser'),
			path: url,
			machineId: machineId ?? undefined,
			browserBaseUrl: proxyBase,
			target: target ?? undefined
		});
		if (viewEntry && viewReady) startSession(viewEntry, tabs.tabs.find((tab) => tab.id === id)!);
	};
	const closeTab = async (id: string) => {
		if (id === mainChatTabId) return;
		if (closingTabIds.has(id)) return;
		const chatView = viewEntry;
		if (!chatView) return;
		closingTabIds.add(id);
		try {
			await chatView.pending.get(id);
			const tab = chatView.state.panels.tabs.find((item) => item.id === id);
			if (!tab) return;
			if (tab.kind === 'page' && !((await pageViews[id]?.requestClose()) ?? true)) return;
			const target =
				tab.sessionId && (tab.kind === 'terminal' || tab.kind === 'browser')
					? resolveTabConnection(tab)
					: null;
			if (
				target &&
				tab.kind === 'terminal' &&
				// An exited or expired shell has nothing left to stop.
				!(chatView === viewEntry && sessionFailures[id]?.status === 404) &&
				!(await new Promise<boolean>((resolve) => {
					stopTerminalChoice = resolve;
				}))
			)
				return;
			if (chatView === viewEntry && fileViews[id]?.hasUnsavedChanges()) {
				selectTab(id);
				if (!(await fileViews[id].requestClose())) return;
			}
			if (tab.kind === 'voice') {
				bridge?.end();
				voiceCall.set(false);
			}
			if (tab.kind === 'preview') showEmbeds.set(false);
			chatView.drafts.delete(id);
			const previousPanels = chatView.state.panels;
			let closedPanels = removeTab(previousPanels, id);
			// a chat's artifacts have nothing to show once the chat is gone
			if (tab.kind === 'chat') closedPanels = removeTab(closedPanels, `artifacts:${id}`);
			changeChatView(chatView, { ...chatView.state, panels: closedPanels });
			if (chatView === viewEntry) {
				tabs = chatView.state.panels;
				delete dirtyFiles[id];
				delete fileContexts[id];
				delete chatStreamingStates[id];
				delete chatTitleEditors[id];
				delete chatTabActions[id];
				delete artifactSelections[id];
				if (tab.kind === 'chat') {
					delete chatArtifacts[id];
					delete artifactSelections[`artifacts:${id}`];
				}
				if (
					!tabs.tabs.length ||
					(!isLargeScreen && tabs.tabs.every((tab) => tab.id === mainChatTabId))
				)
					showTabs.set(false);
				await tick();
				if (chatView === viewEntry) document.getElementById(toTabDomId(tabs.activeId))?.focus();
			}
			if (target && tab.sessionId) {
				try {
					await stopSession(target, tab.kind, tab.sessionId);
				} catch (error) {
					if (!(error instanceof MachineRequestError) || error.status !== 404) {
						changeChatView(chatView, {
							...chatView.state,
							panels:
								chatView.state.panels === closedPanels
									? previousPanels
									: openTab(chatView.state.panels, tab)
						});
						if (chatView === viewEntry) {
							tabs = chatView.state.panels;
							showTabs.set(true);
						}
						throw error;
					}
				}
			}
		} catch (error) {
			toast.error(String(error));
		} finally {
			closingTabIds.delete(id);
		}
	};
	let isTabDropHandled = false;
	const makeTabsSortable = (node: HTMLElement) => {
		let nextSibling: ChildNode | null = null;
		let isTouchDrag = false;
		const trackTouch = (event: TouchEvent) => {
			if (!isTouchDrag) return;
			const point = event.touches[0] ?? event.changedTouches[0];
			chatDropPreview = point
				? getChatDropZone({
						target: document.elementFromPoint(point.clientX, point.clientY),
						clientX: point.clientX,
						clientY: point.clientY,
						dataTransfer: null
					})
				: null;
		};
		const preventTouchMenu = (event: Event) => {
			if ((event.target as Element).closest('[role="tab"]')) event.preventDefault();
		};
		document.addEventListener('touchmove', trackTouch, { passive: true });
		node.addEventListener('contextmenu', preventTouchMenu);
		const sortable = new Sortable(node, {
			animation: 150,
			direction: 'horizontal',
			draggable: '[data-panel-tab]',
			handle: '[role="tab"]',
			delay: 200,
			delayOnTouchOnly: true,
			touchStartThreshold: 5,
			// Touch events let Sortable cancel scrolling after the hold without disabling quick swipes.
			supportPointer: false,
			fallbackOnBody: true,
			ghostClass: 'opacity-40',
			setData: (transfer: DataTransfer, item: HTMLElement) =>
				transfer.setData('application/x-chat-panel-tab', item.dataset.panelTab ?? ''),
			onStart: ({ item, originalEvent }: { item: HTMLElement; originalEvent?: Event }) => {
				nextSibling = item.nextSibling;
				isTouchDrag = !!originalEvent && 'touches' in originalEvent;
				clearChatDropPreview();
				isTabDropHandled = false;
				draggedTabId = item.dataset.panelTab ?? '';
				isDragging = true;
			},
			onEnd: ({
				item,
				from,
				originalEvent
			}: {
				item: HTMLElement;
				from: HTMLElement;
				originalEvent?: Event;
			}) => {
				const cancelled = originalEvent?.type === 'touchcancel';
				if (isTouchDrag && originalEvent && 'touches' in originalEvent)
					trackTouch(originalEvent as TouchEvent);
				const touchTarget = isTouchDrag && !cancelled ? chatDropPreview : null;
				const id = item.dataset.panelTab!;
				const group = groupByTabId[id];
				const order = Array.from(from.querySelectorAll<HTMLElement>('[data-panel-tab]'))
					.map((tab) => tab.dataset.panelTab!)
					.filter((tabId) => group?.tabIds.includes(tabId));
				// Restore the DOM before Svelte reconciles its keyed tabs.
				from.insertBefore(item, nextSibling?.parentNode === from ? nextSibling : null);
				if (touchTarget) {
					tabs = touchTarget.edge
						? splitTab(tabs, id, touchTarget.groupId, touchTarget.edge)
						: moveTabToGroup(tabs, id, touchTarget.groupId);
				} else if (!isTabDropHandled && !cancelled) tabs = moveTab(tabs, id, order.indexOf(id));
				const drop = pendingTabDrop;
				pendingTabDrop = null;
				drop?.();
				// Consume Sortable's fallback click suppression so it cannot swallow the next tap.
				if (isTouchDrag) document.documentElement.dispatchEvent(new MouseEvent('click'));
				draggedTabId = '';
				isDragging = false;
				isTouchDrag = false;
				clearChatDropPreview();
			}
		});
		return {
			destroy: () => {
				sortable.destroy();
				document.removeEventListener('touchmove', trackTouch);
				node.removeEventListener('contextmenu', preventTouchMenu);
			}
		};
	};
	const navigateTabs = async (event: KeyboardEvent) => {
		if (!(event.target instanceof HTMLElement) || event.target.getAttribute('role') !== 'tab')
			return;
		const group = tabs.groups.find((group) => group.id === tabs.activeGroupId)!;
		const index = group.tabIds.indexOf(tabs.activeId);
		if (event.altKey && event.shiftKey && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
			event.preventDefault();
			const tabIndex = groupByTabId[tabs.activeId].tabIds.indexOf(tabs.activeId);
			tabs = moveTab(tabs, tabs.activeId, tabIndex + (event.key === 'ArrowLeft' ? -1 : 1));
			await tick();
			document.getElementById(toTabDomId(tabs.activeId))?.focus();
			return;
		}
		let next = index;
		if (event.key === 'ArrowRight') next = (index + 1) % group.tabIds.length;
		else if (event.key === 'ArrowLeft')
			next = (index - 1 + group.tabIds.length) % group.tabIds.length;
		else if (event.key === 'Home') next = 0;
		else if (event.key === 'End') next = group.tabIds.length - 1;
		else return;
		event.preventDefault();
		selectTab(group.tabIds[next]);
		document.getElementById(toTabDomId(group.tabIds[next]))?.focus();
	};

	$: hasMessages = chatHistory?.messages && Object.keys(chatHistory.messages).length > 0;
	const groupChatTabId = (group: TabGroup) => {
		const tab = tabs.tabs.find((item) => item.id === group.activeId);
		return tab?.kind === 'chat' && tab.id !== mainChatTabId ? tab.id : undefined;
	};
	const groupChatOverview = (group: TabGroup) => {
		const id = groupChatTabId(group);
		return id ? (chatViews[id]?.getOverview() ?? null) : null;
	};

	const chatContextNeedsSavedChat = (machine: any) => machine?.scope === 'chat';
	$: selectedSystemMachine = ($machines ?? []).find(
		(t) => !!$selectedMachineId && t.id === $selectedMachineId
	);
	$: selectedSystemMachineAvailable =
		selectedSystemMachine &&
		!(chatContextNeedsSavedChat(selectedSystemMachine) && !isSavedChatId(chatId));
	$: supportsMachineFiles = !!(
		$config?.features?.enable_tool_servers &&
		$selectedMachineId &&
		selectedSystemMachineAvailable
	);
	$: showFilesTab =
		supportsMachineFiles ||
		(codeInterpreterEnabled && $config?.code?.interpreter_engine !== 'jupyter');
	$: showCommentsTab = !!(
		$config?.features?.enable_comments &&
		$user &&
		isSavedChatId(chatId) &&
		!$temporaryChat
	);
	let commentCount: number | null = null;
	let commentCountRequestId = 0;
	const setCommentCount = (total: number) => {
		++commentCountRequestId;
		commentCount = total;
	};
	const loadCommentCount = async (id: string) => {
		const version = ++commentCountRequestId;
		commentCount = null;
		try {
			const result = await commentsRequest<{ total: number }>(
				`/?${resourceQuery({ resource_type: 'chat', resource_id: id })}&limit=1`
			);
			if (version === commentCountRequestId) commentCount = result.total;
		} catch {
			/* The comments panel handles access errors when opened. */
		}
	};
	$: if (showCommentsTab && $showTabs && chatId) loadCommentCount(chatId);
	let lastCommentLinkHref = '';
	$: if (showCommentsTab && chatId === $page.params.id && $page.url.href !== lastCommentLinkHref) {
		lastCommentLinkHref = $page.url.href;
		const comment_id = $page.url.searchParams.get('comment');
		if (comment_id) showTabs.set({ tab: 'comments', comment_id });
	}
	let currentComments: CommentsRequest | null = null;
	$: currentComments =
		showCommentsTab && chatId
			? {
					resource_type: 'chat',
					resource_id: chatId,
					...commentAnchor
				}
			: null;
	// A chat's artifacts or Overview tab names the chat it belongs to.
	$: tabLabel = (tab: Tab) => {
		if (tab.kind === 'terminal') return terminalTitles[tab.sessionId ?? ''] || tab.label;
		// A cited file or web page names its own tab.
		if (tab.kind === 'preview') return tab.embed?.title || tab.label;
		const source =
			(tab.kind === 'artifacts' || tab.kind === 'overview') &&
			tab.sourceTabId &&
			tab.sourceTabId !== mainChatTabId
				? tabs.tabs.find((item) => item.id === tab.sourceTabId)
				: null;
		return source ? `${tab.label} · ${source.label}` : tab.label;
	};
	$: showArtifactsTab = $mainArtifacts.length > 0 && $visibleControls['chat.artifacts'];
	// A temporary side chat tab keeps no chat id; a citation clicked there comes from the active tab.
	$: embedSourceTab =
		$embed?.chatId && $embed.chatId !== chatId
			? (tabs.tabs.find((tab) => tab.kind === 'chat' && tab.chatId === $embed.chatId) ??
				($showEmbeds &&
				isTemporaryChatId($embed.chatId) &&
				activeTab?.kind === 'chat' &&
				activeTab.id !== mainChatTabId &&
				!activeTab.chatId
					? activeTab
					: undefined))
			: undefined;
	$: showPreviewTab = !!$embed && ($embed.chatId === chatId || !!embedSourceTab);
	$: availableViews = [
		{ kind: 'files', label: $i18n.t('Files'), available: showFilesTab },
		{
			kind: 'chat',
			label: $i18n.t('New Chat'),
			available: canOpenChat
		},
		{ kind: 'artifacts', label: $i18n.t('Artifacts'), available: showArtifactsTab },
		{ kind: 'preview', label: $i18n.t('Preview'), available: showPreviewTab },
		{ kind: 'voice', label: $i18n.t('Voice'), available: !!bridge && $voiceCall },
		{ kind: 'comments', label: $i18n.t('Comments'), available: showCommentsTab }
	];

	$: newTabViews = availableViews.filter(
		(view) => view.kind !== 'files' && view.kind !== 'voice' && view.available
	);
	$: canOpenNewTab =
		showFilesTab ||
		supportsMachineFiles ||
		canSelectMachine ||
		newTabViews.length > 0 ||
		hasMessages;

	const splitWithSuggestedTab = () => {
		if (tabs.tabs.length < 2) {
			const view = availableViews.find((view) => view.available);
			if (!view) return;
			if (view.kind === 'files') openFiles();
			else openFeatureTab(view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'chat');
		}
		tabs = setSplitTabs(tabs, true);
	};

	const toggleSplit = () => {
		if (tabs.groups.length > 1) tabs = setSplitTabs(tabs, false);
		else splitWithSuggestedTab();
	};

	const handleWorkspaceShortcut = (event: KeyboardEvent) => {
		if (
			event.defaultPrevented ||
			event.repeat ||
			$settings?.keyboardShortcuts === false ||
			document.querySelector('.modal, [role="alertdialog"]') ||
			(event.target instanceof Element &&
				event.target.closest('[role="dialog"], [role="menu"], [role="listbox"]'))
		)
			return;

		const shortcut = matchKeybinding(event);
		let action: (() => void) | undefined;
		switch (shortcut) {
			case Shortcut.VOICE_NOTE:
				if (voiceNoteDestination || canVoiceNote || canSelectMachine) action = openVoiceNote;
				break;
			case Shortcut.QUICK_OPEN:
				if (supportsMachineFiles && selectedConnection)
					action = () => {
						showQuickOpen = true;
					};
				break;
			case Shortcut.OPEN_FILES:
				if (showFilesTab || canSelectMachine) action = () => openFiles();
				break;
			case Shortcut.OPEN_DESKTOP:
				if ((supportsDesktop && selectedConnection) || canSelectMachine) action = openDesktop;
				break;
			case Shortcut.NEW_CHAT_TAB:
				if (canOpenChat) action = () => openFeatureTab('chat');
				break;
			case Shortcut.OPEN_COMMENTS:
				if (showCommentsTab) action = () => openFeatureTab('comments');
				break;
			case Shortcut.NEW_FILE:
				if ((supportsMachineFiles && selectedConnection) || canSelectMachine)
					action = openNewFileTab;
				break;
			case Shortcut.NEW_TERMINAL:
				if ((supportsMachine && selectedConnection) || canSelectMachine)
					action = openNewTerminalTab;
				break;
			case Shortcut.NEW_BROWSER:
				if ((supportsBrowser && selectedConnection) || canSelectMachine)
					action = () => openBrowser();
				break;
			case Shortcut.CLOSE_TAB:
				if (panelVisible && tabs.activeId)
					action = () => {
						void closeTab(tabs.activeId);
					};
				break;
			case Shortcut.NEXT_TAB:
			case Shortcut.PREVIOUS_TAB: {
				const group = tabs.groups.find((group) => group.id === tabs.activeGroupId);
				if (!panelVisible || !group || group.tabIds.length < 2) break;
				const index = group.tabIds.indexOf(group.activeId);
				const direction = shortcut === Shortcut.NEXT_TAB ? 1 : -1;
				const id = group.tabIds[(index + direction + group.tabIds.length) % group.tabIds.length];
				action = () => {
					selectTab(id);
					document.getElementById(toTabDomId(id))?.focus();
				};
				break;
			}
			case Shortcut.TOGGLE_SPLIT:
				if (fullWidth && (tabs.tabs.length > 1 || canOpenNewTab)) action = toggleSplit;
				break;
		}
		if (!action) return;
		// Handle before editors and terminals consume the chord, but after modal recording.
		event.preventDefault();
		event.stopPropagation();
		action();
	};

	const isMachineReachable = (machineId: string) => {
		if (!$config?.features?.enable_tool_servers) return false;
		const system = ($machines ?? []).find((machine) => !!machineId && machine.id === machineId);
		return !!system && !(chatContextNeedsSavedChat(system) && !isSavedChatId(chatId));
	};
	$: selectedConnection =
		supportsMachineFiles && isMounted
			? resolveMachineTarget($selectedMachineId, $machines ?? [], localStorage.token ?? '', {
					chatId: panelChatId,
					modelId: modelId ?? null
				})
			: null;
	// Machines this chat can use, offered when terminal tabs are opened before one is selected.
	let availableMachines: MachineOption[] = [];
	$: availableMachines = $config?.features?.enable_tool_servers
		? [
				...($machines ?? [])
					.filter(
						(machine) =>
							machine.id && !(chatContextNeedsSavedChat(machine) && !isSavedChatId(chatId))
					)
					.map((machine) => ({
						id: machine.id,
						label: machine.name || $i18n.t('Machine'),
						device: machine.id.startsWith('tether:')
					}))
			]
		: [];
	$: canSelectMachine = !selectedConnection && availableMachines.length > 0;
	let pendingMachineAction: (() => void) | null = null;
	const askForMachine = (action: () => void) => {
		if (availableMachines.length) pendingMachineAction = action;
	};
	const runWithMachine = async (id: string) => {
		const action = pendingMachineAction;
		pendingMachineAction = null;
		selectMachine(selectedMachineId, id, chatId);
		await tick();
		if (selectedConnection) action?.();
	};
	const loadMachineFeatures = async () => {
		const version = ++featureCheckRequestId;
		supportsMachine = false;
		supportsDesktop = false;
		supportsBrowser = false;
		if (!selectedConnection) return;
		try {
			const result = await machineRequest<{
				features?: { terminal?: boolean; desktop?: boolean; browser?: boolean };
			}>(selectedConnection, '/api/config');
			if (version === featureCheckRequestId) {
				supportsMachine = result.features?.terminal !== false;
				supportsDesktop = result.features?.desktop === true;
				supportsBrowser = result.features?.browser === true;
			}
		} catch {
			/* Files remain available when interactive terminals are disabled. */
		}
	};
	$: {
		selectedConnection;
		panelChatId;
		void loadMachineFeatures();
	}

	$: if (isMounted && !chatLoading && $user?.id) followChat(viewState, panelChatId);
	$: if (
		isMounted &&
		viewReady &&
		!chatLoading &&
		!isLargeScreen &&
		$showTabs === true &&
		tabs.tabs.every((tab) => tab.id === mainChatTabId)
	) {
		const options = [
			...availableViews
				.filter((view) => view.available && view.kind !== 'chat')
				.map((view) => () => {
					if (view.kind === 'files') openFiles();
					else openFeatureTab(view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'chat');
				}),
			...(supportsMachineFiles ? [openNewFileTab] : []),
			...(supportsMachine ? [openNewTerminalTab] : []),
			...(supportsBrowser ? [openBrowser] : []),
			...(supportsDesktop ? [openDesktop] : [])
		];
		if (supportsMachineFiles || (!hasExtraTabs && showFilesTab)) openFiles();
		else if (options.length === 1) options[0]();
		else if (!options.length && !canOpenChat) showTabs.set(false);
		hasExtraTabs = true;
	}
	$: if (
		!canOpenChatTab &&
		$chatTabRequest &&
		'parentChatId' in $chatTabRequest &&
		$chatTabRequest.parentChatId === chatId
	)
		chatTabRequest.set(null);
	$: if (viewReady && $showTabs === 'chat') {
		if (canOpenChatTab) openFeatureTab('chat', true);
		else chatTabRequest.set(null);
		showTabs.set(tabs.tabs.length > 0);
	}
	$: if (
		viewReady &&
		($showTabs === 'comments' || (typeof $showTabs === 'object' && $showTabs)) &&
		showCommentsTab
	) {
		commentAnchor = typeof $showTabs === 'object' ? $showTabs : {};
		openFeatureTab('comments');
	}
	$: if (viewReady && $showEmbeds && showPreviewTab) {
		openPreview();
		showEmbeds.set(false);
	}
	$: if (viewReady && $voiceCall) openFeatureTab('voice');
	$: if (viewReady && !$voiceCall && tabs.tabs.some((tab) => tab.kind === 'voice'))
		closeTab('voice');
	$: if (viewReady && $showTabs === 'voice') openFeatureTab('voice');
	$: if (viewReady && $showFileNav) {
		const request = $showFileNav;
		showFileNav.set(null);
		if (request.chatId === chatId) openFiles(request.machineId, request.directory, true);
	}
	$: if (viewReady && $showFileNavPath && supportsMachineFiles && $selectedMachineId) {
		const request = $showFileNavPath;
		showFileNavPath.set(null);
		openFile(
			typeof request === 'string' ? request : request.path,
			$selectedMachineId,
			typeof request === 'string' ? null : request.page
		);
	}

	beforeNavigate(({ from, to, cancel, willUnload }) => {
		if (from?.url.pathname === to?.url.pathname) {
			// The router stays on the main chat while other tabs are in front; going there uncovers it.
			if (to && location.pathname !== to.url.pathname) {
				// A folder's chats are tabs, opened again by the route.
				if (!mainTabFolder || !to.url.pathname.startsWith('/c/')) focusMainChat();
				if (!isLargeScreen) showTabs.set(false);
			}
			return;
		}
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		if (willUnload && hasChatViewDrafts()) cancel();
	});
	onDestroy(() => {
		stopTerminalChoice?.(false);
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		setView({ status: 'idle' });
		++commentCountRequestId;
		++featureCheckRequestId;
	});

	const handleMediaQuery = (event: MediaQueryList | MediaQueryListEvent) => {
		if (panelTarget && isLargeScreen !== event.matches) releasePanel(panelTarget);
		if (isLargeScreen && !event.matches && tabs.tabs.every((tab) => tab.id === mainChatTabId))
			showTabs.set(false);
		isLargeScreen = event.matches;
	};

	onMount(() => {
		if (appLayout) appLayout.openPageTab = openPageTab;
		const unregisterCapture = registerChatViewCapture(captureView);
		const unsubscribeViews = chatViewChanges.subscribe(() => {
			if (!viewEntry || !viewReady) return;
			tabs = viewEntry.state.panels;
			if (viewState.status === 'ready' && viewState.error !== viewEntry.error)
				setView({ ...viewState, error: viewEntry.error });
		});
		document.addEventListener('keydown', handleWorkspaceShortcut, true);
		const unsubscribeVisibility = showTabs.subscribe((visible) => {
			if (!isLargeScreen && !visible && panelTarget) releasePanel(panelTarget);
		});
		const mediaQuery = window.matchMedia('(min-width: 768px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		let isDestroyed = false;

		const init = async () => {
			await tick();

			if (isDestroyed) return;

			setTimeout(() => {
				isMounted = true;
			}, 0);
		};
		init();

		return () => {
			if (appLayout?.openPageTab === openPageTab) delete appLayout.openPageTab;
			unregisterCapture();
			unsubscribeViews();
			document.removeEventListener('keydown', handleWorkspaceShortcut, true);
			unsubscribeVisibility();
			isDestroyed = true;
			isMounted = false;
			if (!isLargeScreen) {
				showTabs.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
		};
	});
	$: activeChatTabId.set(
		activeTab?.kind === 'chat' && activeTab.id !== mainChatTabId ? (activeTab.chatId ?? null) : null
	);
	onDestroy(() => activeChatTabId.set(null));
	// Tab-opening handlers mutate tabs indirectly, so derive visibility and placement after them.
	$: renderedTabs = fullWidth ? tabs : setMainChatTab(tabs, false);
	$: layoutRects = fullWidth
		? getLayoutRects(renderedTabs.layout)
		: {
				groups: { [renderedTabs.activeGroupId]: { left: 0, top: 0, width: 1, height: 1 } },
				dividers: []
			};
	$: groupByTabId = Object.fromEntries(
		renderedTabs.groups.flatMap((group) => group.tabIds.map((id) => [id, group]))
	);
	$: visibleTabIds = new Set(
		renderedTabs.groups
			.filter((group) => fullWidth || group.id === renderedTabs.activeGroupId)
			.map((group) => group.activeId)
	);
	// A folder remembers many chats; each loads when it is first looked at.
	let seenTabIds = new Set<string>();
	$: if ([...visibleTabIds].some((id) => !seenTabIds.has(id)))
		seenTabIds = new Set([...seenTabIds, ...visibleTabIds]);
	$: mainChatActive = fullWidth && visibleTabIds.has(mainChatTabId);
	$: if (isMounted && viewReady && !chatLoading) {
		const active = tabs.tabs.find((tab) => tab.id === tabs.activeId);
		const href =
			active?.kind === 'page'
				? active.href
				: active?.id === mainChatTabId
					? mainChatHref
					: active?.kind === 'chat'
						? active.chatId
							? `/c/${active.chatId}`
							: active.href
						: null;
		if (href) {
			const url = new URL(href, location.origin);
			if (active?.id === mainChatTabId && !isSavedChatId(chatId)) {
				// delete() re-encodes the other parameters even when it removes nothing.
				if ($temporaryChat !== ($settings?.temporaryChatByDefault ?? false))
					url.searchParams.set('temporary-chat', String($temporaryChat));
				else if (url.searchParams.has('temporary-chat')) url.searchParams.delete('temporary-chat');
			} else if (active?.id === mainChatTabId && url.pathname === get(page).url.pathname) {
				// Keep the query, such as ?message=, so a reload lands there again.
				url.search = get(page).url.search;
			}
			if (url.origin === location.origin && url.href !== location.href) {
				// Reflect selection without routing through SvelteKit and remounting the workspace.
				window.history.replaceState(window.history.state, '', url);
			}
		}
	}
	$: mainChatGroupId =
		renderedTabs.groups.find((group) => group.tabIds.includes(mainChatTabId))?.id ?? '';
	$: mainChatStyle =
		fullWidth && layoutRects.groups[mainChatGroupId]
			? toPaneStyle(layoutRects.groups[mainChatGroupId], 36)
			: '';
</script>

<ConfirmDialog
	show={!!stopTerminalChoice}
	title={$i18n.t('Stop terminal?')}
	message={$i18n.t('Stop this terminal and close the tab?')}
	confirmLabel={$i18n.t('Stop terminal')}
	on:confirm={() => {
		stopTerminalChoice?.(true);
		stopTerminalChoice = null;
	}}
	on:cancel={() => {
		stopTerminalChoice?.(false);
		stopTerminalChoice = null;
	}}
/>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title
		>{activeTab?.kind === 'page' ||
		(activeTab?.kind === 'chat' &&
			activeTab.id !== mainChatTabId &&
			$settings.showChatTitleInTab !== false)
			? `${activeTab.label} / ${$WEBUI_NAME}`
			: $settings.showChatTitleInTab !== false && chatId && title
				? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} / ${$WEBUI_NAME}`
				: $WEBUI_NAME}</title
	>
</svelte:head>

<svelte:window
	bind:innerWidth={viewportWidth}
	on:dragstart|capture={(event) => {
		if (event.target instanceof Element && event.target.closest('#sidebar')) isDragging = true;
	}}
	on:dragend|capture={() => {
		isDragging = false;
		clearChatDropPreview();
	}}
	on:drop|capture={clearChatDropPreview}
	on:blur={clearChatDropPreview}
/>

{#if chatDropPreview}
	<div
		class="chat-drop-preview fixed pointer-events-none z-50 bg-base-1000/[0.02] dark:bg-base-0/[0.02]"
		style:left={`${chatDropPreview.left}px`}
		style:top={`${chatDropPreview.top}px`}
		style:width={`${chatDropPreview.width}px`}
		style:height={`${chatDropPreview.height}px`}
		role="status"
	>
		<div
			class="absolute left-1/2 top-1/2 flex max-w-[calc(100%-1rem)] -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-lg bg-base-0/95 px-2.5 py-1.5 text-xs text-base-600 shadow-sm ring-1 ring-base-1000/5 dark:bg-base-850/95 dark:text-base-300 dark:ring-base-0/10"
		>
			<Icon name="split-horizontal" size={14} strokeWidth={1.5} />
			<span class="truncate">{$i18n.t('Open in side panel')}</span>
		</div>
	</div>
{/if}

{#if voiceNoteDestination}
	{@const target = voiceNoteDestination}
	<VoiceNote
		bind:this={voiceNote}
		{...target}
		canTranscribe={canTranscribeVoiceNote}
		onclose={() => {
			voiceNoteDestination = null;
		}}
		onsaved={(path) => openFile(path, target.target.selector)}
	/>
{/if}

{#if showQuickOpen && supportsMachineFiles && selectedConnection}
	{#key JSON.stringify( [selectedConnection.baseUrl, selectedConnection.context.modelId, panelChatId] )}
		<QuickOpen
			target={selectedConnection}
			chatId={panelChatId}
			onclose={() => {
				showQuickOpen = false;
			}}
			onselect={(path) => openFile(path, selectedConnection!.selector)}
		/>
	{/key}
{/if}

{#if pendingMachineAction}
	<MachinePicker
		options={availableMachines}
		onclose={() => {
			pendingMachineAction = null;
		}}
		onselect={runWithMachine}
	/>
{/if}

<div
	role="presentation"
	on:dragover|capture={handleChatDragOver}
	on:drop|capture={handleChatDrop}
	on:dragleave={handleChatDragLeave}
	class:hidden={!panelVisible || !panelTarget}
	use:placePanel={panelVisible ? panelTarget : null}
	class="h-full w-full min-h-0 flex flex-col {fullWidth
		? 'absolute inset-0 pointer-events-none'
		: ''}"
	style:--chat-tabs-dark-background={'var(--color-base-900)'}
	id="controls-container"
>
	<div bind:this={paneCanvas} class="relative flex-1 min-h-0 min-w-0">
		{#if viewError}
			<div
				role="alert"
				class="absolute inset-x-0 top-10 z-40 pointer-events-auto bg-base-0 dark:bg-base-900 p-3 text-sm"
			>
				{viewError}
				<button
					class="underline ml-2"
					on:click={() => {
						if (viewState.status === 'attachFailed')
							void attachChatViewTo(viewState.chatId).catch(() => {});
						else if (viewState.status === 'ready') void flushChatView(viewState.entry);
						else if (viewState.status === 'loadFailed') void restoreChatView(viewState.chatId);
					}}>{$i18n.t('Retry')}</button
				>
			</div>
		{:else if chatLoading || (!viewReady && !mainChatActive)}
			<div
				role="status"
				aria-label={$i18n.t('Loading…')}
				class="absolute inset-0 flex items-center justify-center text-sm text-base-500"
			>
				<Spinner className="size-5" />
			</div>
		{/if}
		{#if fullWidth && viewReady && !chatLoading}
			<button
				type="button"
				class="absolute right-2 top-1 z-20 flex size-7 items-center justify-center rounded-lg text-base-500 hover:bg-base-50/40 dark:text-base-400 dark:hover:bg-base-800/40 disabled:opacity-30 pointer-events-auto"
				aria-label={$i18n.t('Split screen')}
				title={[
					$i18n.t('Split screen'),
					$settings?.keyboardShortcuts !== false ? formatChord($keybindings.toggleSplit) : ''
				]
					.filter(Boolean)
					.join(' · ')}
				aria-pressed={tabs.groups.length > 1}
				disabled={tabs.tabs.length < 2 && !canOpenNewTab}
				on:click={toggleSplit}
			>
				<SplitPanel className="size-4.5" strokeWidth="1" />
			</button>
		{/if}
		{#each renderedTabs.groups.filter((group) => fullWidth || group.id === renderedTabs.activeGroupId) as group (group.id)}
			<div
				data-panel-group={group.id}
				role="presentation"
				class="absolute min-h-0 min-w-0 pointer-events-none flex flex-col overflow-hidden"
				style={toPaneStyle(layoutRects.groups[group.id])}
				on:focusin={(event) => focusGroup(group.id, event)}
				on:pointerdown={(event) => focusGroup(group.id, event)}
			>
				{@render tabBar(group)}
			</div>
		{/each}
		{#each layoutRects.dividers as divider (divider.id)}
			<div
				role="separator"
				tabindex="0"
				aria-label={$i18n.t('Resize panels')}
				aria-orientation={divider.direction === 'horizontal' ? 'vertical' : 'horizontal'}
				aria-valuemin={20}
				aria-valuemax={80}
				aria-valuenow={Math.round(divider.ratio * 100)}
				class="absolute z-30 pointer-events-auto touch-none group {divider.direction ===
				'horizontal'
					? 'w-1 -translate-x-1/2 cursor-col-resize'
					: 'h-1 -translate-y-1/2 cursor-row-resize'}"
				style:left={`${(divider.left + (divider.direction === 'horizontal' ? divider.width * divider.ratio : 0)) * 100}%`}
				style:top={`${(divider.top + (divider.direction === 'vertical' ? divider.height * divider.ratio : 0)) * 100}%`}
				style:width={divider.direction === 'vertical' ? `${divider.width * 100}%` : undefined}
				style:height={divider.direction === 'horizontal' ? `${divider.height * 100}%` : undefined}
				on:pointerdown={(event) => startSplitResize(event, divider)}
				on:pointermove={moveSplitResize}
				on:pointerup={endSplitResize}
				on:pointercancel={endSplitResize}
				on:keydown={(event) => {
					if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
					event.preventDefault();
					tabs = {
						...tabs,
						layout: resizeSplit(
							tabs.layout,
							divider.id,
							divider.ratio + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -0.05 : 0.05)
						)
					};
				}}
			>
				<div
					class="absolute bg-base-200/40 dark:bg-base-850/20 group-hover:bg-base-300/60 dark:group-hover:bg-base-800 transition-colors {divider.direction ===
					'horizontal'
						? 'inset-y-0 left-1/2 w-px'
						: 'inset-x-0 top-1/2 h-px'}"
				></div>
			</div>
		{/each}
		{#each (viewReady ? tabs.tabs : []).filter((tab) => tab.id !== mainChatTabId && (tab.kind !== 'chat' || !mainTabFolder || seenTabIds.has(tab.id))) as tab (tab.kind === 'page' ? tab.id : `${viewEntry?.instanceId}:${tab.id}`)}
			{@const chatView = viewEntry!}
			{@const target =
				isMounted && $config && $user && $settings && $machines !== null
					? resolveTabConnection(tab)
					: null}
			{@const failure = sessionFailures[tab.id]}
			<div
				id={`${toTabDomId(tab.id)}-view`}
				role="tabpanel"
				aria-labelledby={toTabDomId(tab.id)}
				class="min-h-0 min-w-0 pointer-events-auto overflow-hidden"
				data-panel-group={groupByTabId[tab.id]?.id}
				style={layoutRects.groups[groupByTabId[tab.id]?.id]
					? toPaneStyle(layoutRects.groups[groupByTabId[tab.id].id], 36)
					: 'display:none'}
				class:hidden={!visibleTabIds.has(tab.id)}
				on:focusin={() => focusGroup(groupByTabId[tab.id].id)}
				on:pointerdown={() => focusGroup(groupByTabId[tab.id].id)}
			>
				{#if tab.machineId && !target}
					<div
						role="status"
						class="flex h-full items-center justify-center p-4 text-center text-xs text-base-400 dark:text-base-500"
					>
						{$i18n.t('Machine unavailable')}
					</div>
				{:else if tab.kind === 'page' && tab.href}
					<Page
						bind:this={pageViews[tab.id]}
						href={tab.href}
						active={visibleTabIds.has(tab.id)}
						onNavigate={(href) => navigatePageTab(tab.id, href)}
						onTitleChange={(label) => {
							if (label && tabs.tabs.find((item) => item.id === tab.id)?.label !== label)
								updateViewTab(chatView, tab.id, { label });
						}}
					/>
				{:else if tab.kind === 'voice' && bridge}
					<CallPanel
						{bridge}
						bind:callMode
						bind:files
						{submitPrompt}
						{stopResponse}
						{modelId}
						chatId={chatId ?? ''}
						{eventTarget}
						on:close={() => closeTab(tab.id)}
					/>
				{:else if tab.kind === 'preview'}
					{#if tab.embed?.file?.knowledgeId}
						<Knowledge embed={tab.embed} chatId={chatId ?? ''} />
					{:else}
						<Embeds embed={tab.embed} overlay={isDragging} />
					{/if}
				{:else if tab.kind === 'artifacts'}
					{@const source = tabs.tabs.find((item) => item.id === tab.sourceTabId)}
					<Artifacts
						overlay={isDragging}
						artifacts={getArtifactsStore(tab.sourceTabId)}
						selection={artifactSelections[tab.id] ?? null}
						chatId={(source?.id !== mainChatTabId && source?.kind === 'chat'
							? source.chatId
							: chatView.chatId) ?? ''}
					/>
				{:else if tab.kind === 'overview'}
					{#await import('./Overview.svelte') then { default: Overview }}
						{@const sourceTabId =
							tab.sourceTabId && tab.sourceTabId !== mainChatTabId ? tab.sourceTabId : null}
						{@const sourceChat = sourceTabId
							? (chatViews[sourceTabId]?.getOverview() ?? null)
							: null}
						<Overview
							history={sourceChat?.history ?? chatHistory}
							chatUser={sourceChat ? sourceChat.chatUser : chatUser}
							onNodeClick={(e: any) => {
								const { node } = e;
								const target = sourceChat?.history ?? chatHistory;
								target.messages[node.data.message.id].favorite = node.data.message.favorite
									? true
									: null;
								if (sourceChat && sourceTabId) {
									if (!visibleTabIds.has(sourceTabId)) selectTab(sourceTabId);
									sourceChat.showMessage(node.data.message, true);
									return;
								}
								if (!visibleTabIds.has(mainChatTabId)) focusMainChat();
								showMessage(node.data.message, true);
							}}
						/>
					{/await}
				{:else if tab.kind === 'chat'}
					<ChatTab
						bind:this={chatViews[tab.id]}
						bind:streaming={chatStreamingStates[tab.id]}
						bind:tabTitleEditor={chatTitleEditors[tab.id]}
						bind:tabActions={chatTabActions[tab.id]}
						artifacts={getChatArtifacts(tab.id)}
						onOpenArtifacts={(code) => openArtifacts(code, tab.id)}
						initialView={chatView.transient[`chat:${tab.id}`]}
						chatId={tab.chatId ?? ''}
						onChatUpdate={(chat) =>
							updateViewTab(chatView, tab.id, {
								chatId: chat.id,
								...(chat.title ? { label: chat.title } : {})
							})}
						parentChatId={tab.parentChatId ?? ''}
						parentFolderId={tab.href ? null : folderId}
						history={chatHistory}
						modelId={tab.href
							? (new URL(tab.href, location.origin).searchParams.get('models') ??
								new URL(tab.href, location.origin).searchParams.get('model') ??
								modelId)
							: modelId}
						{systemPrompt}
						initialPrompt={tab.initialPrompt ?? ''}
					/>
				{:else if tab.kind === 'comments' && currentComments}
					{#key `${$user?.id}:$chatId={chatView.chatId}:${currentComments.comment_id ?? ''}`}
						<CommentsPanel
							embedded={true}
							bind:view={currentComments}
							onCountChange={setCommentCount}
						/>
					{/key}
				{:else if tab.kind === 'desktop' && target}
					{#key target.context.modelId}
						<Desktop
							target={target!}
							chatId={chatView.chatId}
							active={panelVisible && visibleTabIds.has(tab.id)}
							overlay={isDragging}
						/>
					{/key}
				{:else if tab.kind === 'browser' || tab.kind === 'terminal'}
					{#if chatView.pending.has(tab.id)}
						<p
							role="status"
							class="flex h-full items-center justify-center p-4 text-center text-xs text-base-400 dark:text-base-500"
						>
							{$i18n.t('Connecting…')}
						</p>
					{:else if !tab.sessionId || failure}
						<div
							role="status"
							class="flex h-full flex-col items-center justify-center gap-3 p-4 text-center text-xs text-base-400 dark:text-base-500"
						>
							<p>
								{failure?.status === 404
									? $i18n.t('Session no longer available')
									: (failure?.message ??
										chatView.sessionErrors[tab.id] ??
										$i18n.t('Session no longer available'))}
							</p>
							{#if failure && failure.status !== 404}
								<button
									class="underline"
									on:click={() => {
										delete sessionFailures[tab.id];
										sessionFailures = { ...sessionFailures };
										sessionAttempts = {
											...sessionAttempts,
											[tab.id]: (sessionAttempts[tab.id] ?? 0) + 1
										};
									}}>{$i18n.t('Retry')}</button
								>
							{:else}
								<button class="underline" on:click={() => startSession(chatView, tab)}
									>{$i18n.t(
										tab.kind === 'terminal' ? 'Start new terminal' : 'Reopen browser'
									)}</button
								>
							{/if}
						</div>
					{:else}
						{#key `${tab.sessionId}:${sessionAttempts[tab.id] ?? 0}`}
							{#if tab.kind === 'terminal'}
								<XTerminal
									bind:this={terminalViews[tab.id]}
									target={target!}
									sessionId={tab.sessionId}
									active={panelVisible && visibleTabIds.has(tab.id)}
									overlay={isDragging}
									onTitleChange={(title, process) => {
										if (chatView !== viewEntry) return;
										terminalTitles[tab.sessionId!] = title.trim();
										terminalProcesses[tab.sessionId!] = process;
									}}
									onUnavailable={(message, status) => {
										if (chatView === viewEntry)
											sessionFailures = { ...sessionFailures, [tab.id]: { message, status } };
									}}
								/>
							{:else}
								<Browser
									bind:this={browserViews[tab.id]}
									baseUrl={getBrowserBaseUrl(target!)}
									{target}
									sessionId={tab.sessionId}
									active={panelVisible && visibleTabIds.has(tab.id)}
									overlay={isDragging}
									onOpenBrowser={(url) => openBrowser(undefined, tab.machineId, undefined, url)}
									onNavigate={(path, label) => updateViewTab(chatView, tab.id, { path, label })}
									onUnavailable={(message, status) => {
										if (chatView === viewEntry)
											sessionFailures = { ...sessionFailures, [tab.id]: { message, status } };
									}}
								/>
							{/if}
						{/key}
					{/if}
				{:else if tab.untitled && target}
					<UntitledFile
						initialView={chatView.drafts.get(tab.id)}
						bind:this={fileViews[tab.id]}
						bind:dirty={dirtyFiles[tab.id]}
						label={tab.label}
						target={target!}
						initialDirectory={tab.context?.currentDirectory}
						isOpen={(path) =>
							tabs.tabs.some(
								(item) =>
									item.id !== tab.id &&
									item.kind === 'file' &&
									!item.untitled &&
									item.machineId === tab.machineId &&
									item.path === path
							)}
						onSaved={(path) => {
							chatView.drafts.delete(tab.id);
							updateViewTab(chatView, tab.id, {
								untitled: false,
								dirty: false,
								path,
								label: path.split('/').pop() || path
							});
						}}
					/>
				{:else if (tab.kind === 'files' || tab.kind === 'file') && tab.machineId}
					{@const fileTarget = isMounted ? resolveTabConnection(tab) : null}
					<div class="flex h-full min-h-0 flex-col">
						<div class="min-h-0 flex-1">
							{#key tab.kind === 'file' ? fileTarget?.context.modelId : null}
								{#await import('./FileNav.svelte') then { default: FileNav }}
									<FileNav
										target={fileTarget}
										modelId={fileTarget?.context.modelId ?? null}
										onFileSaved={(content) => {
											const draft = chatView.drafts.get(tab.id);
											if (draft?.preview) {
												draft.preview.baseText = content;
												draft.dirty = draft.preview.dirty = draft.preview.text !== content;
											}
										}}
										initialView={chatView.drafts.get(tab.id)}
										onViewChange={(view) => {
											chatView.drafts.set(tab.id, view);
											if (tab.kind === 'files')
												updateViewTab(chatView, tab.id, {
													directory: view.directory,
													label: view.isHome
														? $i18n.t('Home')
														: view.directory?.split('/').filter(Boolean).pop() || $i18n.t('Files')
												});
										}}
										onFilesMoved={() => {
											if (chatView !== viewEntry) return;
											for (const other of tabs.tabs) {
												if (
													other.id !== tab.id &&
													other.kind === 'files' &&
													other.machineId === tab.machineId
												)
													void fileViews[other.id]?.refreshDirectory?.();
											}
										}}
										gitStatus={fileGitStatuses[tab.machineId] ?? null}
										gitTarget={fileTarget}
										gitDiffMode={fileGitDiffModes[tab.machineId] ?? 'unified'}
										gitHideWhitespace={fileGitHideWhitespace[tab.machineId] ?? false}
										bind:this={fileViews[tab.id]}
										bind:dirty={dirtyFiles[tab.id]}
										machineId={tab.machineId}
										initialFile={tab.kind === 'file' ? { path: tab.path!, page: tab.page } : null}
										initialDirectory={tab.kind === 'files'
											? (tab.directory ?? tab.path ?? null)
											: null}
										active={panelVisible && visibleTabIds.has(tab.id)}
										manageFileRequests={false}
										showTerminalDock={tab.kind === 'files'}
										onOpenFile={(path, page) =>
											openFile(path, tab.machineId!, page, fileTarget?.context.modelId)}
										onBrowseDirectory={(path) =>
											openFiles(tab.machineId, path, false, fileTarget?.context.modelId)}
										{onAskFile}
										overlay={isDragging}
										chatId={chatView.chatId}
										bind:machineContext={fileContexts[tab.id]}
									/>
								{/await}
							{/key}
						</div>
						{#if tab.kind === 'files' && fileTarget}
							<GitBar
								bind:this={gitViews[tab.id]}
								initialView={chatView.transient[`git:${tab.id}`]}
								bind:status={fileGitStatuses[tab.machineId]}
								bind:diffMode={fileGitDiffModes[tab.machineId]}
								bind:hideWhitespace={fileGitHideWhitespace[tab.machineId]}
								target={fileTarget}
								chatId={chatView.chatId}
								directory={fileContexts[tab.id]?.currentDirectory ??
									tab.directory ??
									tab.path ??
									'.'}
								active={panelVisible && visibleTabIds.has(tab.id)}
								onOpenFile={(path) =>
									openFile(path, tab.machineId!, null, fileTarget?.context.modelId)}
								onOpenDirectory={(path) =>
									openFiles(tab.machineId, path, false, fileTarget?.context.modelId)}
								{onDraftPrompt}
							/>
						{/if}
					</div>
				{:else if tab.kind === 'files' && codeInterpreterEnabled}
					<PyodideFileNav overlay={isDragging} />
				{/if}
			</div>
		{/each}
		<!-- The mobile drawer hides the main chat tab, so count what it actually shows. -->
		{#if viewReady && !chatLoading && !viewError && !renderedTabs.tabs.length && (canOpenNewTab || !isLargeScreen)}<div
				class="flex h-full items-center justify-center p-3 text-center text-xs text-base-500 dark:text-base-400"
			>
				{canOpenNewTab ? $i18n.t('Open a tab using the + menu.') : $i18n.t('No open tabs')}
			</div>{/if}
	</div>
</div>

{#snippet tabBar(group: TabGroup)}
	<div
		data-panel-tab-bar
		class="flex h-9 items-center px-1.5 {fullWidth &&
		layoutRects.groups[group.id]?.top === 0 &&
		layoutRects.groups[group.id].left + layoutRects.groups[group.id].width > 0.999
			? 'pr-10'
			: ''} gap-1 shrink-0 pointer-events-auto select-none col-start-1 row-start-1 min-w-0 z-10"
	>
		<div class="flex items-center gap-0.5 flex-1 min-w-0 py-0.5">
			<div
				role="tablist"
				data-swipe-no-gesture
				use:makeTabsSortable
				tabindex="-1"
				aria-label={$i18n.t('Tabs')}
				on:keydown={navigateTabs}
				class="panel-tab-strip flex items-center gap-0.5 min-w-0 overflow-x-auto"
				on:wheel|nonpassive={(event) => {
					const strip = event.currentTarget;
					if (
						event.ctrlKey ||
						event.shiftKey ||
						Math.abs(event.deltaY) <= Math.abs(event.deltaX) ||
						strip.scrollWidth <= strip.clientWidth
					)
						return;
					const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? strip.clientWidth : 1;
					event.preventDefault();
					strip.scrollLeft += event.deltaY * unit;
				}}
			>
				{#each group.tabIds.map((id) => tabs.tabs.find((tab) => tab.id === id)!) as tab (tab.id)}
					{@const titleEditor =
						tab.id === mainChatTabId
							? mainTabFolder
								? undefined
								: tabTitleEditor
							: chatTitleEditors[tab.id]}
					{@const PageIcon =
						tab.kind === 'page' ? pageIcons[tab.href?.split(/[/?#]/)[1] ?? ''] : null}
					<div
						role="presentation"
						data-panel-tab={tab.id}
						use:activateFilesOnDrag={tab}
						on:click={() => selectTab(tab.id)}
						class="panel-tab flex cursor-pointer items-center gap-1.5 ps-2.5 pe-2 h-7 rounded-lg text-sm font-normal whitespace-nowrap shrink-0 transition {group.activeId ===
						tab.id
							? 'bg-base-100/40 dark:bg-base-800/25 text-base-700 dark:text-base-200'
							: 'text-base-500 dark:text-base-400 hover:bg-base-100/30 dark:hover:bg-base-800/20 hover:text-base-600 dark:hover:text-base-300'}"
					>
						<button
							role="tab"
							aria-keyshortcuts={tab.id === mainChatTabId
								? undefined
								: 'Alt+Shift+ArrowLeft Alt+Shift+ArrowRight'}
							id={toTabDomId(tab.id)}
							aria-controls={`${toTabDomId(tab.id)}-view`}
							aria-selected={group.activeId === tab.id}
							tabindex={group.activeId === tab.id ? 0 : -1}
							title={tab.id === mainChatTabId
								? mainTabTitle
								: (tab.directory ?? tab.path ?? tabLabel(tab))}
							aria-label={tab.id === mainChatTabId ? mainTabTitle : undefined}
							class="flex h-full items-center gap-1.5 min-w-0"
							on:dblclick={() => {
								if (tab.kind === 'chat') void chatViews[tab.id]?.startRename();
								if (tab.id !== mainChatTabId) return;
								if (mainTabFolder) void startFolderRename();
								else onRenameMainTab?.();
							}}
						>
							{#if (tab.id === mainChatTabId && chatStreaming) || (tab.kind === 'chat' && chatStreamingStates[tab.id])}
								<Spinner className="size-3.5" />
								<span class="sr-only">{$i18n.t('Generating...')}</span>
							{:else if tab.id === mainChatTabId && mainTabFolder}
								{#if mainTabFolder.icon}
									<Emoji shortCode={mainTabFolder.icon} className="size-3.5" />
								{:else}
									<FolderIcon className="size-3.5 shrink-0" strokeWidth="2" />
								{/if}
							{:else if tab.kind === 'preview' && tab.embed?.file?.knowledgeId}
								<Database className="size-3.5 shrink-0" />
							{:else if tab.kind === 'file' || (tab.kind === 'preview' && tab.embed?.file)}
								<Icon name={fileIconName(tabLabel(tab))} size={14} strokeWidth={1.4} />
							{:else if tab.kind === 'terminal'}
								<Icon
									name={terminalIconName(
										terminalProcesses[tab.sessionId ?? ''] ?? '',
										tabLabel(tab)
									)}
									size={14}
								/>
							{:else if tab.kind === 'comments'}
								<Annotation className="size-3.5 shrink-0" />
							{:else if tab.kind === 'overview'}
								<Map className="size-3.5 shrink-0" strokeWidth="1.5" />
							{:else if PageIcon}
								<svelte:component this={PageIcon} className="size-3.5 shrink-0" />
							{:else}
								<Icon name={getTabIcon(tab.kind)} size={14} />
							{/if}
							{#if !titleEditor && !(tab.id === mainChatTabId && mainTabFolder && isRenamingFolder)}
								<span class="max-w-30 overflow-hidden text-ellipsis"
									>{tab.id === mainChatTabId ? mainTabTitle : tabLabel(tab)}</span
								>
							{/if}
							{#if tab.kind === 'comments' && commentCount}<span class="text-base-400"
									>{commentCount}</span
								>{/if}
						</button>
						{@render titleEditor?.()}
						{#if tab.untitled || dirtyFiles[tab.id]}<span
								class="ms-1 size-1.5 shrink-0 rounded-full bg-base-400"
								aria-label={$i18n.t('Unsaved changes')}
							></span>{/if}
						{#if tab.id === mainChatTabId}
							{#if mainTabFolder && isRenamingFolder}
								<input
									data-folder-tab-rename
									bind:value={folderNameDraft}
									class="min-w-0 flex-1 bg-transparent text-sm font-normal text-base-700 outline-hidden dark:text-base-300"
									aria-label={$i18n.t('Folder Name')}
									on:click|stopPropagation
									on:keydown={(e) => {
										if (e.isComposing || e.keyCode === 229) return;
										if (e.key === 'Enter') {
											e.preventDefault();
											void saveFolderRename();
										} else if (e.key === 'Escape') {
											e.preventDefault();
											isRenamingFolder = false;
										}
									}}
									on:blur={saveFolderRename}
								/>
							{/if}
							{@render tabActions?.()}
						{:else if !titleEditor}{#if chatTabActions[tab.id]}<span class="-me-1 flex"
									>{@render chatTabActions[tab.id]?.()}</span
								>{/if}<button
								type="button"
								class="flex items-center justify-center w-4 h-4 rounded text-base-400 hover:bg-base-200 hover:text-base-700 dark:hover:bg-base-0/10 dark:hover:text-base-0"
								title={[
									$i18n.t('Close'),
									$settings?.keyboardShortcuts !== false ? formatChord($keybindings.closeTab) : ''
								]
									.filter(Boolean)
									.join(' · ')}
								aria-label={tab.kind === 'voice'
									? $i18n.t('End call')
									: `${$i18n.t('Close')} ${tabLabel(tab)}`}
								on:click|stopPropagation={() => closeTab(tab.id)}
								><Icon name="xmark" size={12} /></button
							>{/if}
					</div>
				{/each}
			</div>
			{#if canOpenNewTab && viewReady && !chatLoading}
				<Dropdown align="start" closeOnSelect>
					<button
						type="button"
						class="flex items-center justify-center w-7 h-7 rounded-lg text-base-400 hover:text-base-600 dark:hover:text-base-300 transition-colors duration-100 shrink-0"
						aria-label={$i18n.t('New tab')}><Icon name="plus" size={14} /></button
					>
					<div slot="content">
						<DropdownMenu className="min-w-56">
							{#if showFilesTab || canSelectMachine}
								<button on:click={() => openFiles($selectedMachineId, undefined, true)}
									><Icon name="folder" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Files')}</span
									><HotkeyHint name="openFiles" className="ms-auto" /></button
								>
							{/if}
							{#if supportsMachineFiles || canSelectMachine}<button on:click={openNewFileTab}
									><Icon name="page" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('New File')}</span
									><HotkeyHint name="newFile" className="ms-auto" /></button
								>{/if}
							{#if supportsMachine || canSelectMachine}<button on:click={openNewTerminalTab}
									><Icon name="terminal" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('New Terminal')}</span
									><HotkeyHint name="newTerminal" className="ms-auto" /></button
								>{/if}
							{#if canVoiceNote || canSelectMachine}
								<button on:click={openVoiceNote}>
									<Icon name="microphone" size={14} />
									<span class="flex-1 text-start">{$i18n.t('Voice Note')}</span>
									<HotkeyHint name="voiceNote" className="ms-auto" />
								</button>
							{/if}
							{#if supportsBrowser || canSelectMachine}<button on:click={() => openBrowser()}
									><Icon name="browser" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Browser')}</span
									><HotkeyHint name="newBrowser" className="ms-auto" /></button
								>{/if}
							{#if supportsDesktop || canSelectMachine}<button on:click={openDesktop}
									><Icon name="monitor" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Desktop')}</span
									><HotkeyHint name="openDesktop" className="ms-auto" /></button
								>{/if}
							{#each newTabViews.filter((view) => view.kind !== 'artifacts') as view}
								<button
									on:click={() =>
										openFeatureTab(
											view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'chat'
										)}
								>
									{#if view.kind === 'comments'}
										<Annotation className="size-3.5 shrink-0" />
									{:else}
										<Icon name={getTabIcon(view.kind as Tab['kind'])} size={14} />
									{/if}<span class="flex-1 text-start">{view.label}</span>
									{#if view.kind === 'chat'}
										<HotkeyHint name="newChatTab" className="ms-auto" />
									{:else if view.kind === 'comments'}
										<HotkeyHint name="openComments" className="ms-auto" />
									{/if}
								</button>
							{/each}
							{#if groupChatOverview(group) ? Object.keys(groupChatOverview(group)?.history?.messages ?? {}).length > 0 : hasMessages}
								<button on:click={() => openOverview(groupChatTabId(group))}>
									<Map className="size-3.5 shrink-0" strokeWidth="1.5" />
									<span class="flex-1 text-start">{$i18n.t('Overview')}</span>
								</button>
							{/if}
							{#if showArtifactsTab}
								<button on:click={() => openFeatureTab('artifacts')}>
									<Icon name={getTabIcon('artifacts')} size={14} />
									<span class="flex-1 text-start">{$i18n.t('Artifacts')}</span>
								</button>
							{/if}
						</DropdownMenu>
					</div>
				</Dropdown>
			{/if}
		</div>
		{#if group.activeId === mainChatTabId}
			<div class="flex shrink-0 items-center gap-2">
				{@render tabBarActions?.()}
			</div>
		{/if}
		{#if !fullWidth && (!isLargeScreen || group.id === tabs.groups[0].id)}
			<button
				type="button"
				class="flex items-center justify-center w-7 h-7 rounded-lg text-base-400 hover:text-base-600 dark:hover:text-base-300 transition-colors duration-100 shrink-0"
				on:click={() => showTabs.set(false)}
				aria-label={$i18n.t('Hide tabs')}><Icon name="xmark" size={12} /></button
			>
		{/if}
	</div>
{/snippet}

{#if !isLargeScreen}
	<MobileSwipePanel
		open={!!$showTabs}
		enabled={$mobile}
		side="right"
		blocked={$showSidebar}
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
				className="min-h-[100dvh] !bg-base-0 dark:!bg-base-900"
			>
				<div use:preservePanel bind:this={panelTarget} class="h-[100dvh] flex flex-col"></div>
			</Drawer>
		{/if}
	</MobileSwipePanel>
{:else if fullWidth}
	<!-- Keep the mounted panel in the main chat's layout container. -->
	<div use:preservePanel bind:this={panelTarget} class="contents"></div>
{/if}

<style>
	.panel-tab {
		-webkit-touch-callout: none;
	}

	.panel-tab:not(:has(:global(button:not([role='tab'])))) {
		padding-inline: 0.625rem;
	}

	.panel-tab-strip {
		scrollbar-width: none;
	}
	.panel-tab-strip::-webkit-scrollbar {
		display: none;
	}
</style>
