<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import type { GitStatus } from '$lib/apis/terminal/git';
	let fileGitStatuses: Record<string, GitStatus | null> = {};
	let fileGitDiffModes: Record<string, 'unified' | 'split'> = {};
	let fileGitHideWhitespace: Record<string, boolean> = {};
	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
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
	import {
		artifactContents,
		config,
		embed,
		temporaryChatEnabled,
		terminalServers,
		showTabs,
		sideChatRequest,
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

	import {
		emptyTabs,
		openTab,
		openTabInSidePanel,
		activateTab,
		removeTab,
		moveTab,
		moveTabToGroup,
		splitTab,
		resizeSplit,
		panelPositions,
		type PanelGroup,
		type PanelRect,
		type PanelDivider,
		type SplitEdge,
		mainChatTabId,
		setMainChatTab,
		setSplitTabs,
		fileTabId,
		type PanelTab
	} from './ChatTabs/tabs';
	import {
		resolveTerminalConnection,
		terminalRequest,
		TerminalRequestError,
		type TerminalConnection
	} from '$lib/apis/terminal';
	import { formatChord, keybindings, matchKeybinding, Shortcut } from '$lib/shortcuts';
	import HotkeyHint from '../common/HotkeyHint.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Dropdown from '../common/Dropdown.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';
	import Icon from './FileNav/Icon.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import { fileIconName } from './FileNav/fileIcon';
	import UntitledFile from './ChatTabs/UntitledFile.svelte';
	import QuickOpen from './ChatTabs/QuickOpen.svelte';
	import VoiceNote from './ChatTabs/VoiceNote.svelte';
	import Browser from './ChatTabs/Browser.svelte';
	import Desktop from './ChatTabs/Desktop.svelte';
	import XTerminal from './XTerminal.svelte';
	import CallPanel from './MessageInput/CallPanel.svelte';
	import Drawer from '../common/Drawer.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';
	import GitBar from './ChatTabs/GitBar.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatTabs/Embeds.svelte';
	import SideChat from './ChatTabs/SideChat.svelte';
	import FileNav from './FileNav.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import Overview from './Overview.svelte';
	import Modal from '../common/Modal.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	let stopTerminalChoice: ((stop: boolean) => void) | null = null;
	import XMark from '../icons/XMark.svelte';
	import SplitPanel from '../icons/SplitPanel.svelte';
	import { isSavedChatId } from '$lib/utils/chatId';

	const i18n = getContext<any>('i18n');

	export let history;

	export let chatId: string | null = null;
	export let chatLoading = false;
	export let folderId: string | null = null;
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
	export let files: any[];
	export let modelId;
	export let systemPrompt = '';
	export let canSideChat = false;

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
	export let tabTitleEditor: import('svelte').Snippet | undefined = undefined;
	export let tabActions: import('svelte').Snippet | undefined = undefined;
	export let tabBarActions: import('svelte').Snippet | undefined = undefined;
	$: fullWidth = largeScreen;
	$: panelVisible = largeScreen || !!$showTabs;

	let largeScreen = false;
	let dragged = false;
	let mounted = false;
	let viewportWidth = 0;

	let tabs = emptyTabs();
	const paneStyle = (rect: PanelRect, header = 0) =>
		`position:absolute;left:${rect.left * 100}%;top:calc(100% * ${rect.top} + ${header}px * var(--app-text-scale, 1));width:${rect.width * 100}%;height:calc(100% * ${rect.height} - ${header}px * var(--app-text-scale, 1));`;
	const focusGroup = (id: string, event?: Event) => {
		// Tab clicks activate their own group.
		if (event?.target instanceof Element && event.target.closest('[data-panel-tab]')) return;
		const group = tabs.groups.find((group) => group.id === id);
		if (group?.activeId && tabs.activeGroupId !== id) tabs = activateTab(tabs, group.activeId);
	};
	let terminalViews: Record<string, XTerminal> = {};
	export const hasTerminals = () => tabs.tabs.some((tab) => tab.kind === 'terminal');
	let browserViews: Record<string, Browser> = {};
	let gitViews: Record<string, GitBar> = {};
	let sideViews: Record<string, SideChat> = {};
	let viewEntry: ReturnType<typeof chatViewEntry> | null = null;
	let viewReady = false;
	let viewError = '';
	let switchVersion = 0;
	let promotion: Promise<void> | null = null;
	let sessionFailures: Record<string, { message: string; status?: number }> = {};
	let sessionAttempts: Record<string, number> = {};

	export function captureView() {
		if (!viewEntry || !viewReady) return;
		const owner = viewEntry;
		for (const tab of tabs.tabs) {
			const draft = fileViews[tab.id]?.captureView?.();
			if (draft) owner.drafts.set(tab.id, draft);
			if (gitViews[tab.id]) owner.transient[`git:${tab.id}`] = gitViews[tab.id].captureView();
			if (sideViews[tab.id]) owner.transient[`side:${tab.id}`] = sideViews[tab.id].captureView();
		}
		owner.transient.gitDiffModes = fileGitDiffModes;
		owner.transient.gitHideWhitespace = fileGitHideWhitespace;
		const panels = {
			...tabs,
			tabs: tabs.tabs.map((tab) => ({
				...tab,
				...(tab.kind === 'files' && owner.drafts.get(tab.id)?.directory
					? { directory: owner.drafts.get(tab.id).directory }
					: {})
			}))
		};
		changeChatView(owner, { ...owner.state, panels, selectedTerminalId: $selectedTerminalId });
	}
	export function prepareChatSwitch() {
		stopTerminalChoice?.(false);
		stopTerminalChoice = null;
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		viewReady = false;
		tabs = emptyTabs();
		++switchVersion;
		tabsChatId = undefined;
	}
	export async function bindTerminalChat(id: string) {
		if (!viewEntry || viewEntry.chatId === id) return;
		if (promotion) return promotion;
		const owner = viewEntry;
		captureView();
		promotion = promoteChatView(
			owner,
			id,
			async () => {
				await tick();
				for (const tab of owner.state.panels.tabs) {
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
			$temporaryChatEnabled
		)
			.then(() => {
				tabsChatId = id;
				viewEntry = owner;
				viewError = '';
			})
			.finally(() => {
				promotion = null;
			});
		return promotion;
	}

	async function restoreChatView(id: string | null) {
		if (!$user?.id) return;
		const version = ++switchVersion;
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		viewReady = false;
		tabs = emptyTabs();
		viewError = '';
		tabsChatId = id;
		const owner = chatViewEntry($user.id, id, $temporaryChatEnabled);
		viewEntry = owner;
		try {
			await loadChatView(owner);
			if (version !== switchVersion) return;
			if (!owner.transient.initialized && !owner.state.panels.tabs.length)
				owner.state.selectedTerminalId = $selectedTerminalId;
			owner.state.panels = setMainChatTab(owner.state.panels, true, title);
			owner.transient.initialized = true;
			tabs = owner.state.panels;
			selectedTerminalId.set(owner.state.selectedTerminalId);
			dirtyFiles = {};
			fileContexts = {};
			fileGitStatuses = {};
			fileGitDiffModes = owner.transient.gitDiffModes ?? {};
			fileGitHideWhitespace = owner.transient.gitHideWhitespace ?? {};
			commentTarget = {};
			sessionFailures = {};
			sessionAttempts = {};
			viewReady = true;
			hasOpenedTabs = tabs.tabs.some((tab) => tab.kind !== 'chat');
		} catch (error) {
			if (version === switchVersion) viewError = String(error);
		}
	}
	const persistPanels = (panels: typeof tabs, selector: string | null, ready: boolean) => {
		if (!ready || !viewEntry || chatLoading || viewEntry.promoting) return;
		// The Files tab follows the terminal picked for the chat and starts over there.
		if (selector && selector !== viewEntry.state.selectedTerminalId) {
			const moved = panels.tabs.filter(
				(tab) => tab.kind === 'files' && tab.terminalId !== selector
			);
			for (const tab of moved) {
				viewEntry.drafts.delete(tab.id);
				delete fileContexts[tab.id];
			}
			panels = {
				...panels,
				tabs: panels.tabs.map((tab) =>
					moved.includes(tab)
						? {
								...tab,
								label: $i18n.t('Files'),
								terminalId: selector,
								path: undefined,
								directory: undefined
							}
						: tab
				)
			};
		}
		if (viewEntry.state.panels !== panels || viewEntry.state.selectedTerminalId !== selector)
			changeChatView(viewEntry, { ...viewEntry.state, panels, selectedTerminalId: selector });
	};
	$: persistPanels(tabs, $selectedTerminalId, viewReady);
	$: if (viewEntry && viewEntry.userId !== $user?.id) {
		viewReady = false;
		viewEntry = null;
		tabs = emptyTabs();
		tabsChatId = undefined;
		clearChatViews();
	}
	const captureConnections = (..._connections: unknown[]) => {
		captureView();
		// A returning component must read disk before restoring its cached draft.
		for (const tab of tabs.tabs) {
			if (tab.terminalId && !terminalAccessible(tab.terminalId)) delete dirtyFiles[tab.id];
		}
		dirtyFiles = { ...dirtyFiles };
	};
	$: if (mounted && viewReady) captureConnections($terminalServers, $settings, $config, $user);
	const tabConnection = (tab: PanelTab) =>
		tab.terminalId && terminalAccessible(tab.terminalId)
			? resolveTerminalConnection(
					tab.terminalId,
					$terminalServers ?? [],
					directTerminals,
					localStorage.token ?? ''
				)
			: null;
	const startSession = (owner: NonNullable<typeof viewEntry>, tab: PanelTab) => {
		const connection = tabConnection(tab);
		if (connection) {
			delete sessionFailures[tab.id];
			void createViewSession(owner, tab.id, connection);
		}
	};

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
	let fileContexts: Record<string, TerminalContext | null> = {};
	let panelTarget: HTMLElement | null = null;
	let tabsChatId: string | null | undefined = undefined;
	let hasOpenedTabs = false;
	let commentTarget: { comment_id?: string } = {};
	let closing = new Set<string>();
	let selectedConnection: TerminalConnection | null = null;
	let showQuickOpen = false;
	let voiceNote: VoiceNote;
	let voiceNoteTarget: {
		connection: TerminalConnection;
		chatId: string | null;
		directory?: string;
	} | null = null;
	$: canVoiceNote = terminalFilesAvailable && !!$user;
	$: canTranscribeVoiceNote = $user?.role === 'admin' || ($user?.permissions?.chat?.stt ?? true);
	const openVoiceNote = () => {
		if (voiceNoteTarget) {
			voiceNote?.finishRecording();
			return;
		}
		if (!canVoiceNote || !selectedConnection || !$user) return;
		voiceNoteTarget = {
			connection: selectedConnection,
			chatId,
			directory:
				contextTab?.terminalId === selectedConnection.selector
					? terminalContext?.currentDirectory
					: undefined
		};
	};
	$: if (!terminalFilesAvailable) showQuickOpen = false;
	let terminalEnabled = false;
	let desktopEnabled = false;
	let browserEnabled = false;
	let featureVersion = 0;
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
	const tabIcon = (kind: PanelTab['kind']) =>
		({
			chat: 'chat-lines',
			files: 'folder',
			file: 'page',
			terminal: 'terminal',
			browser: 'browser',
			desktop: 'monitor',
			artifacts: 'code',
			preview: 'browser',
			voice: 'microphone',
			comments: 'chat-bubble',
			side: 'chat-lines'
		})[kind];
	const domId = (id: string) => `chat-panel-${encodeURIComponent(id)}`;
	$: activeTabId = tabs.activeId;
	$: activeTab = tabs.tabs.find((tab) => tab.id === tabs.activeId);
	$: contextTab =
		activeTab?.kind === 'chat'
			? tabs.tabs.find((tab) => tab.id === tabs.history.at(-1))
			: activeTab;
	const syncTerminalContext = (context: TerminalContext | null) => {
		if (context) terminalContext = context;
		else if (terminalContext?.file) terminalContext = { ...terminalContext, file: null };
	};
	$: syncTerminalContext(
		(contextTab && fileContexts[contextTab.id]) ?? contextTab?.context ?? null
	);
	$: if (activeTabId && panelTarget) {
		const id = activeTabId;
		void tick().then(() =>
			document
				.getElementById(domId(id))
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
	const activateFilesOnDrag = (node: HTMLElement, tab: PanelTab) => {
		if (tab.kind !== 'files') return;
		let timer: ReturnType<typeof setTimeout> | undefined;
		const clear = () => {
			clearTimeout(timer);
			timer = undefined;
		};
		const over = (event: DragEvent) => {
			if (!event.dataTransfer?.types.includes('application/x-terminal-file-move') || timer) return;
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
	const openPanel = (tab: PanelTab, inSidePanel = false) => {
		if (!viewReady || !viewEntry) return;
		hasOpenedTabs = true;
		tabs = inSidePanel ? openTabInSidePanel(tabs, tab) : openTab(tabs, tab);
		changeChatView(viewEntry, { ...viewEntry.state, panels: tabs });
		showTabs.set(true);
	};
	const openFiles = (selector = $selectedTerminalId, directory?: string, newTab = false) => {
		if (selector ? !terminalAccessible(selector) : !showFilesTab) return;
		directory ??=
			terminalContext?.terminalId === selector
				? terminalContext.currentDirectory || undefined
				: undefined;
		const existing = newTab
			? undefined
			: (tabs.tabs.find(
					(tab) =>
						tab.id === tabs.activeId &&
						tab.kind === 'files' &&
						(tab.terminalId ?? null) === selector
				) ??
				tabs.tabs.find((tab) => tab.kind === 'files' && (tab.terminalId ?? null) === selector));
		const id = existing?.id ?? uuidv4();
		openPanel({
			id,
			kind: 'files',
			label: $i18n.t('Files'),
			terminalId: selector ?? undefined,
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
	const openFile = (path: string, selector: string, page?: number | null) => {
		if (!terminalAccessible(selector)) return;
		path = path.replace(/\\/g, '/').replace(/\/{2,}/g, '/');
		const id =
			tabs.tabs.find(
				(tab) =>
					tab.kind === 'file' && !tab.untitled && tab.terminalId === selector && tab.path === path
			)?.id ?? fileTabId(selector, path);
		openPanel({
			id,
			kind: 'file',
			label: path.split('/').pop() || path,
			terminalId: selector,
			path,
			page
		});
		if (page != null) fileViews[id]?.revealPage?.(page);
	};
	const newFile = () => {
		if (!terminalFilesAvailable || !selectedConnection) return;
		let number = 1;
		while (tabs.tabs.some((tab) => tab.untitled && tab.label === `Untitled-${number}`)) number++;
		openPanel({
			id: uuidv4(),
			kind: 'file',
			label: `Untitled-${number}`,
			terminalId: selectedConnection.selector,
			connection: { ...selectedConnection },
			untitled: true,
			context: contextTab?.terminalId === selectedConnection.selector ? terminalContext : undefined
		});
	};
	const openFeature = (
		kind: 'artifacts' | 'preview' | 'voice' | 'comments' | 'side',
		inSidePanel = false
	) => {
		if (!availableViews.some((view) => view.kind === kind && view.available)) return;
		const view = availableViews.find((view) => view.kind === kind)!;
		if (kind === 'side') {
			let sideChatNumber = 1;
			while (tabs.tabs.some((tab) => tab.kind === 'side' && tab.sideChatNumber === sideChatNumber))
				sideChatNumber++;
			const pending = $sideChatRequest;
			const initialPrompt = pending?.parentId === chatId ? pending.prompt : '';
			if (pending?.parentId === chatId) sideChatRequest.set(null);
			openPanel(
				{
					id: uuidv4(),
					kind,
					label: `${view.label} ${sideChatNumber}`,
					sideChatNumber,
					initialPrompt
				},
				inSidePanel
			);
			return;
		}
		openPanel({ id: kind, kind, label: view.label }, inSidePanel);
	};

	type SplitDrop = PanelRect & { groupId: string; edge: SplitEdge | null };
	let chatDropPreview: SplitDrop | null = null;
	let draggedTabId = '';
	let pendingTabDrop: (() => void) | null = null;
	const clearChatDropPreview = () => (chatDropPreview = null);
	const canDropChat = (event: Pick<DragEvent, 'dataTransfer'>) =>
		canSideChat &&
		($user?.role === 'admin' ||
			!(
				($user?.permissions?.chat?.temporary ?? true) &&
				($user?.permissions?.chat?.temporary_enforced ?? false)
			)) &&
		event.dataTransfer?.types.includes('application/x-open-webui-chat');
	const chatDropBounds = (
		event: Pick<DragEvent, 'target' | 'clientX' | 'clientY' | 'dataTransfer'>
	): SplitDrop | null => {
		const internal =
			!!draggedTabId || event.dataTransfer?.types.includes('application/x-chat-panel-tab');
		if ((!internal && !canDropChat(event)) || !(event.target instanceof Element)) return null;
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
			if (!$showTabs && largeScreen) return null;
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
	export const dragOverChat = (event: DragEvent) => {
		chatDropPreview = chatDropBounds(event);
		if (chatDropPreview || event.dataTransfer?.types.includes('Files')) event.preventDefault();
		if (chatDropPreview)
			event.dataTransfer!.dropEffect = event.dataTransfer!.types.includes(
				'application/x-chat-panel-tab'
			)
				? 'move'
				: 'copy';
	};
	export const leaveChatDrop = (event: DragEvent) => {
		if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node))
			clearChatDropPreview();
	};
	export const dropChat = (event: DragEvent) => {
		const bounds = chatDropBounds(event);
		clearChatDropPreview();
		if (event.dataTransfer?.types.includes('Files')) event.preventDefault();
		if (!bounds || pendingTabDrop) return;
		const internalId = event.dataTransfer?.getData('application/x-chat-panel-tab');
		let savedId = '';
		if (internalId) {
			if (!tabs.tabs.some((tab) => tab.id === internalId)) return;
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
			if (savedId === chatId && !tabs.tabs.some((tab) => tab.id === mainChatTabId)) return;
			const existing =
				internalId ||
				(savedId === chatId ? mainChatTabId : tabs.tabs.find((tab) => tab.chatId === savedId)?.id);
			let id = existing;
			if (!id) {
				focusGroup(groupId);
				id = uuidv4();
				tabs = openTab(tabs, { id, kind: 'side', label: $i18n.t('Chat'), chatId: savedId });
			}
			tabs = bounds.edge
				? splitTab(tabs, id, groupId, bounds.edge)
				: moveTabToGroup(tabs, id, groupId);
			showTabs.set(true);
		};
		if (internalId) {
			// Let Sortable restore its source DOM before changing the keyed tab groups.
			tabDropHandled = true;
			pendingTabDrop = applyDrop;
		} else {
			event.stopPropagation();
			applyDrop();
		}
	};

	let resizingSplit: PanelDivider | null = null;
	const startSplitResize = (event: PointerEvent, divider: PanelDivider) => {
		event.preventDefault();
		resizingSplit = divider;
		dragged = true;
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
		dragged = false;
	};
	const newTerminal = () => {
		if (!terminalEnabled || !selectedConnection) return;
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
			terminalId: selectedConnection.selector,
			connection: { ...selectedConnection }
		});
		if (viewEntry && viewReady) startSession(viewEntry, tabs.tabs.find((tab) => tab.id === id)!);
	};
	const openDesktop = () => {
		if (!desktopEnabled || !selectedConnection) return;
		openPanel({
			id: JSON.stringify(['desktop', selectedConnection.selector]),
			kind: 'desktop',
			label: $i18n.t('Desktop'),
			terminalId: selectedConnection.selector,
			connection: { ...selectedConnection }
		});
	};
	const openBrowser = (
		port?: number,
		selector = $selectedTerminalId,
		baseUrl?: string,
		initialUrl?: string
	) => {
		if (!selector || !terminalAccessible(selector)) return;
		if (selector === $selectedTerminalId && !browserEnabled) return;
		const url = initialUrl ?? (port ? `http://localhost:${port}/` : undefined);
		const existing =
			url &&
			tabs.tabs.find(
				(tab) => tab.kind === 'browser' && tab.terminalId === selector && tab.path === url
			);
		if (existing) {
			selectTab(existing.id);
			return;
		}
		const connection = selector
			? resolveTerminalConnection(
					selector,
					$terminalServers ?? [],
					directTerminals,
					localStorage.token ?? ''
				)
			: null;
		if (!connection) return;
		const terminal = ($terminalServers ?? []).find((item) => item.id === selector);
		const proxyBase =
			baseUrl ??
			(connection && chatContextNeedsSavedChat(terminal) && chatId
				? `${connection.baseUrl}/chats/${encodeURIComponent(chatId)}`
				: connection?.baseUrl);
		const id = uuidv4();
		openPanel({
			id,
			kind: 'browser',
			label: port ? `localhost:${port}` : $i18n.t('Browser'),
			path: url,
			terminalId: selector ?? undefined,
			browserBaseUrl: proxyBase,
			connection: connection ?? undefined
		});
		if (viewEntry && viewReady) startSession(viewEntry, tabs.tabs.find((tab) => tab.id === id)!);
	};
	const closeTab = async (id: string) => {
		if (id === mainChatTabId) return;
		if (closing.has(id)) return;
		const owner = viewEntry;
		if (!owner) return;
		closing.add(id);
		try {
			await owner.pending.get(id);
			const tab = owner.state.panels.tabs.find((item) => item.id === id);
			if (!tab) return;
			const connection =
				tab.sessionId && (tab.kind === 'terminal' || tab.kind === 'browser')
					? tabConnection(tab)
					: null;
			if (
				connection &&
				tab.kind === 'terminal' &&
				!(await new Promise<boolean>((resolve) => {
					stopTerminalChoice = resolve;
				}))
			)
				return;
			if (owner === viewEntry && fileViews[id]?.hasUnsavedChanges()) {
				selectTab(id);
				if (!(await fileViews[id].requestClose())) return;
			}
			if (tab.kind === 'voice') {
				bridge?.end();
				showCallOverlay.set(false);
			}
			if (tab.kind === 'artifacts') showArtifacts.set(false);
			if (tab.kind === 'preview') showEmbeds.set(false);
			owner.drafts.delete(id);
			const previousPanels = owner.state.panels;
			const closedPanels = removeTab(previousPanels, id);
			changeChatView(owner, { ...owner.state, panels: closedPanels });
			if (owner === viewEntry) {
				tabs = owner.state.panels;
				delete dirtyFiles[id];
				delete fileContexts[id];
				if (!tabs.tabs.length || (!largeScreen && tabs.tabs.every((tab) => tab.kind === 'chat')))
					showTabs.set(false);
				await tick();
				if (owner === viewEntry) document.getElementById(domId(tabs.activeId))?.focus();
			}
			if (connection && tab.sessionId) {
				try {
					await terminalRequest(
						connection,
						owner.chatId,
						`${tab.kind === 'terminal' ? '/api/terminals' : '/browser/sessions'}/${encodeURIComponent(tab.sessionId)}`,
						{ method: 'DELETE' }
					);
				} catch (error) {
					if (!(error instanceof TerminalRequestError) || error.status !== 404) {
						changeChatView(owner, {
							...owner.state,
							panels:
								owner.state.panels === closedPanels
									? previousPanels
									: openTab(owner.state.panels, tab)
						});
						if (owner === viewEntry) {
							tabs = owner.state.panels;
							showTabs.set(true);
						}
						throw error;
					}
				}
			}
		} catch (error) {
			toast.error(String(error));
		} finally {
			closing.delete(id);
		}
	};
	let tabDropHandled = false;
	const sortableTabs = (node: HTMLElement) => {
		let nextSibling: ChildNode | null = null;
		let touchDrag = false;
		const trackTouch = (event: TouchEvent) => {
			if (!touchDrag) return;
			const point = event.touches[0] ?? event.changedTouches[0];
			chatDropPreview = point
				? chatDropBounds({
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
				touchDrag = !!originalEvent && 'touches' in originalEvent;
				clearChatDropPreview();
				tabDropHandled = false;
				draggedTabId = item.dataset.panelTab ?? '';
				dragged = true;
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
				if (touchDrag && originalEvent && 'touches' in originalEvent)
					trackTouch(originalEvent as TouchEvent);
				const touchTarget = touchDrag && !cancelled ? chatDropPreview : null;
				const id = item.dataset.panelTab!;
				const group = tabGroups[id];
				const order = Array.from(from.querySelectorAll<HTMLElement>('[data-panel-tab]'))
					.map((tab) => tab.dataset.panelTab!)
					.filter((tabId) => group?.tabIds.includes(tabId));
				// Restore the DOM before Svelte reconciles its keyed tabs.
				from.insertBefore(item, nextSibling?.parentNode === from ? nextSibling : null);
				if (touchTarget) {
					tabs = touchTarget.edge
						? splitTab(tabs, id, touchTarget.groupId, touchTarget.edge)
						: moveTabToGroup(tabs, id, touchTarget.groupId);
				} else if (!tabDropHandled && !cancelled) tabs = moveTab(tabs, id, order.indexOf(id));
				const drop = pendingTabDrop;
				pendingTabDrop = null;
				drop?.();
				// Consume Sortable's fallback click suppression so it cannot swallow the next tap.
				if (touchDrag) document.documentElement.dispatchEvent(new MouseEvent('click'));
				draggedTabId = '';
				dragged = false;
				touchDrag = false;
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
	const navigateTabs = (event: KeyboardEvent) => {
		if (!(event.target instanceof HTMLElement) || event.target.getAttribute('role') !== 'tab')
			return;
		const group = tabs.groups.find((group) => group.id === tabs.activeGroupId)!;
		const index = group.tabIds.indexOf(tabs.activeId);
		if (event.altKey && event.shiftKey && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
			event.preventDefault();
			const tabIndex = tabGroups[tabs.activeId].tabIds.indexOf(tabs.activeId);
			tabs = moveTab(tabs, tabs.activeId, tabIndex + (event.key === 'ArrowLeft' ? -1 : 1));
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
		document.getElementById(domId(group.tabIds[next]))?.focus();
	};

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
	$: if (showCommentsTab && $showTabs && chatId) loadCommentCount(chatId);
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
					...commentTarget
				}
			: null;
	$: showArtifactsTab = ($artifactContents ?? []).length > 0 && $visibleControls['chat.artifacts'];
	$: showPreviewTab = !!$embed && $embed.chatId === chatId;
	$: availableViews = [
		{ kind: 'files', label: $i18n.t('Files'), available: showFilesTab },
		{
			kind: 'side',
			label: $i18n.t('New Chat'),
			available: canSideChat
		},
		{ kind: 'artifacts', label: $i18n.t('Artifacts'), available: showArtifactsTab },
		{ kind: 'preview', label: $i18n.t('Preview'), available: showPreviewTab },
		{ kind: 'voice', label: $i18n.t('Voice'), available: $showCallOverlay },
		{ kind: 'comments', label: $i18n.t('Comments'), available: showCommentsTab }
	];

	$: newTabViews = availableViews.filter(
		(view) => view.kind !== 'files' && view.kind !== 'voice' && view.available
	);
	$: canOpenNewTab = showFilesTab || terminalFilesAvailable || newTabViews.length > 0;

	const quickSplit = () => {
		if (tabs.tabs.length < 2) {
			const view = availableViews.find((view) => view.available);
			if (!view) return;
			if (view.kind === 'files') openFiles();
			else openFeature(view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'side');
		}
		tabs = setSplitTabs(tabs, true);
	};

	const toggleSplit = () => {
		if (tabs.groups.length > 1) tabs = setSplitTabs(tabs, false);
		else quickSplit();
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
				if (voiceNoteTarget || canVoiceNote) action = openVoiceNote;
				break;
			case Shortcut.QUICK_OPEN:
				if (terminalFilesAvailable && selectedConnection)
					action = () => {
						showQuickOpen = true;
					};
				break;
			case Shortcut.OPEN_FILES:
				if (showFilesTab) action = () => openFiles();
				break;
			case Shortcut.OPEN_DESKTOP:
				if (desktopEnabled && selectedConnection) action = openDesktop;
				break;
			case Shortcut.NEW_CHAT_TAB:
				if (canSideChat) action = () => openFeature('side');
				break;
			case Shortcut.OPEN_COMMENTS:
				if (showCommentsTab) action = () => openFeature('comments');
				break;
			case Shortcut.NEW_FILE:
				if (terminalFilesAvailable && selectedConnection) action = newFile;
				break;
			case Shortcut.NEW_TERMINAL:
				if (terminalEnabled && selectedConnection) action = newTerminal;
				break;
			case Shortcut.NEW_BROWSER:
				if (browserEnabled && selectedConnection) action = () => openBrowser();
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
					document.getElementById(domId(id))?.focus();
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

	$: directTerminals =
		($settings as { terminalServers?: { url: string; key?: string }[] })?.terminalServers ?? [];
	const terminalAccessible = (selector: string) => {
		if (!$config?.features?.enable_tool_servers) return false;
		const system = ($terminalServers ?? []).find((terminal) => terminal.id === selector);
		if (system)
			return (
				chatContextAvailable(system) &&
				!(chatContextNeedsSavedChat(system) && !isSavedChatId(chatId))
			);
		return !!(
			$config?.features?.enable_direct_integrations &&
			($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true)) &&
			directTerminals.some((terminal) => terminal.url === selector)
		);
	};
	$: selectedConnection =
		terminalFilesAvailable && mounted
			? resolveTerminalConnection(
					$selectedTerminalId,
					$terminalServers ?? [],
					directTerminals,
					localStorage.token ?? ''
				)
			: null;
	const checkTerminal = async () => {
		const version = ++featureVersion;
		terminalEnabled = false;
		desktopEnabled = false;
		browserEnabled = false;
		if (!selectedConnection) return;
		try {
			const result = await terminalRequest<{
				features?: { terminal?: boolean; desktop?: boolean; browser?: boolean };
			}>(selectedConnection, chatId, '/api/config');
			if (version === featureVersion) {
				terminalEnabled = result.features?.terminal !== false;
				desktopEnabled = result.features?.desktop === true;
				browserEnabled = result.features?.browser === true;
			}
		} catch {
			/* Files remain available when interactive terminals are disabled. */
		}
	};
	$: {
		selectedConnection;
		chatId;
		void checkTerminal();
	}

	$: if (mounted && !chatLoading && $user?.id && chatId !== tabsChatId) {
		if (viewEntry && !viewEntry.chatId && chatId && viewReady) {
			tabsChatId = chatId;
			void bindTerminalChat(chatId).catch((error) => {
				viewError = String(error);
			});
		} else void restoreChatView(chatId);
	}
	$: if (
		mounted &&
		viewReady &&
		!chatLoading &&
		!largeScreen &&
		$showTabs === true &&
		tabs.tabs.every((tab) => tab.id === mainChatTabId)
	) {
		const options = [
			...availableViews
				.filter((view) => view.available && view.kind !== 'side')
				.map((view) => () => {
					if (view.kind === 'files') openFiles();
					else openFeature(view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'side');
				}),
			...(terminalFilesAvailable ? [newFile] : []),
			...(terminalEnabled ? [newTerminal] : []),
			...(browserEnabled ? [openBrowser] : []),
			...(desktopEnabled ? [openDesktop] : [])
		];
		if (terminalFilesAvailable || (!hasOpenedTabs && showFilesTab)) openFiles();
		else if (options.length === 1) options[0]();
		else if (!options.length && !canSideChat) showTabs.set(false);
		hasOpenedTabs = true;
	}
	$: if (
		!(
			$user?.role === 'admin' ||
			($user?.role === 'user' && ($user.permissions?.chat?.side_chat ?? false))
		) &&
		$sideChatRequest?.parentId === chatId
	)
		sideChatRequest.set(null);
	$: if (viewReady && $showTabs === 'side') {
		if (canSideChat) openFeature('side', true);
		else sideChatRequest.set(null);
		showTabs.set(tabs.tabs.length > 0);
	}
	$: if (
		viewReady &&
		($showTabs === 'comments' || (typeof $showTabs === 'object' && $showTabs)) &&
		showCommentsTab
	) {
		commentTarget = typeof $showTabs === 'object' ? $showTabs : {};
		openFeature('comments');
	}
	$: if (viewReady && $showArtifacts && showArtifactsTab) {
		openFeature('artifacts', true);
		showArtifacts.set(false);
	}
	$: if (viewReady && $showEmbeds && showPreviewTab) {
		openFeature('preview');
		showEmbeds.set(false);
	}
	$: if (viewReady && $showCallOverlay) openFeature('voice');
	$: if (viewReady && $showTabs === 'voice') openFeature('voice');
	$: if (viewReady && $showFileNavPath && terminalFilesAvailable && $selectedTerminalId) {
		const request = $showFileNavPath;
		showFileNavPath.set(null);
		openFile(
			typeof request === 'string' ? request : request.path,
			$selectedTerminalId,
			typeof request === 'string' ? null : request.page
		);
	}

	beforeNavigate(({ from, to, cancel, willUnload }) => {
		if (from?.url.pathname === to?.url.pathname) return;
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		if (willUnload && hasChatViewDrafts()) cancel();
	});
	onDestroy(() => {
		stopTerminalChoice?.(false);
		captureView();
		if (viewEntry) void flushChatView(viewEntry);
		++switchVersion;
		++countVersion;
		++featureVersion;
		showOverview.set(false);
	});

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

	const handleMediaQuery = (event: MediaQueryList | MediaQueryListEvent) => {
		if (panelTarget && largeScreen !== event.matches) releasePanel(panelTarget);
		largeScreen = event.matches;
	};

	onMount(() => {
		const unregisterCapture = registerChatViewCapture(captureView);
		const unsubscribeViews = chatViewChanges.subscribe(() => {
			if (viewEntry && viewReady) {
				tabs = viewEntry.state.panels;
				viewError = viewEntry.error;
			}
		});
		document.addEventListener('keydown', handleWorkspaceShortcut, true);
		const unsubscribeVisibility = showTabs.subscribe((visible) => {
			if (!largeScreen && !visible && panelTarget) releasePanel(panelTarget);
		});
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

		return () => {
			unregisterCapture();
			unsubscribeViews();
			document.removeEventListener('keydown', handleWorkspaceShortcut, true);
			unsubscribeVisibility();
			isDestroyed = true;
			mounted = false;
			if (!largeScreen) {
				showTabs.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
		};
	});
	// Tab-opening handlers mutate tabs indirectly, so derive visibility and placement after them.
	$: displayTabs = fullWidth ? tabs : setMainChatTab(tabs, false);
	$: positions = fullWidth
		? panelPositions(displayTabs.layout)
		: {
				groups: { [displayTabs.activeGroupId]: { left: 0, top: 0, width: 1, height: 1 } },
				dividers: []
			};
	$: tabGroups = Object.fromEntries(
		displayTabs.groups.flatMap((group) => group.tabIds.map((id) => [id, group]))
	);
	$: visibleTabIds = new Set(
		displayTabs.groups
			.filter((group) => fullWidth || group.id === displayTabs.activeGroupId)
			.map((group) => group.activeId)
	);
	$: mainChatActive = fullWidth && visibleTabIds.has(mainChatTabId);
	$: mainChatGroupId =
		displayTabs.groups.find((group) => group.tabIds.includes(mainChatTabId))?.id ?? '';
	$: mainChatStyle =
		fullWidth && positions.groups[mainChatGroupId]
			? paneStyle(positions.groups[mainChatGroupId], 36)
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

<svelte:window
	bind:innerWidth={viewportWidth}
	on:dragend={clearChatDropPreview}
	on:drop|capture={clearChatDropPreview}
	on:blur={clearChatDropPreview}
/>

{#if chatDropPreview}
	<div
		class="chat-drop-preview fixed pointer-events-none z-50 bg-black/[0.02] dark:bg-white/[0.02]"
		style:left={`${chatDropPreview.left}px`}
		style:top={`${chatDropPreview.top}px`}
		style:width={`${chatDropPreview.width}px`}
		style:height={`${chatDropPreview.height}px`}
		role="status"
	>
		<div
			class="absolute left-1/2 top-1/2 flex max-w-[calc(100%-1rem)] -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-lg bg-white/95 px-2.5 py-1.5 text-xs text-gray-600 shadow-sm ring-1 ring-black/5 dark:bg-gray-850/95 dark:text-gray-300 dark:ring-white/10"
		>
			<Icon name="split-horizontal" size={14} strokeWidth={1.5} />
			<span class="truncate">{$i18n.t('Open in side panel')}</span>
		</div>
	</div>
{/if}

{#if voiceNoteTarget}
	{@const target = voiceNoteTarget}
	<VoiceNote
		bind:this={voiceNote}
		{...target}
		canTranscribe={canTranscribeVoiceNote}
		onclose={() => {
			voiceNoteTarget = null;
		}}
		onsaved={(path) => openFile(path, target.connection.selector)}
	/>
{/if}

{#if showQuickOpen && terminalFilesAvailable && selectedConnection}
	{#key `${selectedConnection.selector}:${chatId}`}
		<QuickOpen
			connection={selectedConnection}
			{chatId}
			onclose={() => {
				showQuickOpen = false;
			}}
			onselect={(path) => openFile(path, selectedConnection!.selector)}
		/>
	{/key}
{/if}

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

<div
	role="presentation"
	on:dragover|capture={dragOverChat}
	on:drop|capture={dropChat}
	on:dragleave={leaveChatDrop}
	class:hidden={!panelVisible || !panelTarget}
	use:placePanel={panelVisible ? panelTarget : null}
	class="h-full w-full min-h-0 flex flex-col {fullWidth
		? 'absolute inset-0 pointer-events-none'
		: ''}"
	style:--chat-tabs-dark-background={'var(--color-gray-900)'}
	id="controls-container"
>
	<div bind:this={paneCanvas} class="relative flex-1 min-h-0 min-w-0">
		{#if viewError}
			<div
				role="alert"
				class="absolute inset-x-0 top-10 z-40 pointer-events-auto bg-white dark:bg-gray-900 p-3 text-sm"
			>
				{viewError}
				<button
					class="underline ml-2"
					on:click={() => {
						if (viewEntry?.promoting && chatId) void bindTerminalChat(chatId).catch(() => {});
						else if (viewReady && viewEntry) void flushChatView(viewEntry);
						else void restoreChatView(chatId);
					}}>{$i18n.t('Retry')}</button
				>
			</div>
		{:else if chatLoading || !viewReady}
			<div
				role="status"
				aria-label={$i18n.t('Loading…')}
				class="absolute inset-0 flex items-center justify-center text-sm text-gray-500"
			>
				<Spinner className="size-5" />
			</div>
		{/if}
		{#if fullWidth && viewReady && !chatLoading}
			<button
				type="button"
				class="absolute right-2 top-1 z-20 flex size-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-50/40 dark:text-gray-400 dark:hover:bg-gray-800/40 disabled:opacity-30 pointer-events-auto"
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
		{#each displayTabs.groups.filter((group) => fullWidth || group.id === displayTabs.activeGroupId) as group (group.id)}
			<div
				data-panel-group={group.id}
				role="presentation"
				class="absolute min-h-0 min-w-0 pointer-events-none flex flex-col overflow-hidden"
				style={paneStyle(positions.groups[group.id])}
				on:focusin={(event) => focusGroup(group.id, event)}
				on:pointerdown={(event) => focusGroup(group.id, event)}
			>
				{@render tabBar(group)}
			</div>
		{/each}
		{#each positions.dividers as divider (divider.id)}
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
					class="absolute bg-gray-50 dark:bg-gray-850/30 group-hover:bg-gray-200 dark:group-hover:bg-gray-800 transition-colors {divider.direction ===
					'horizontal'
						? 'inset-y-0 left-1/2 w-px'
						: 'inset-x-0 top-1/2 h-px'}"
				></div>
			</div>
		{/each}
		{#each (viewReady ? tabs.tabs : []).filter((tab) => tab.kind !== 'chat') as tab (`${viewEntry?.instanceId}:${tab.id}`)}
			{@const owner = viewEntry!}
			{@const connection =
				mounted && $config && $user && $settings && $terminalServers !== null
					? tabConnection(tab)
					: null}
			{@const failure = sessionFailures[tab.id]}
			<div
				id={`${domId(tab.id)}-view`}
				role="tabpanel"
				aria-labelledby={domId(tab.id)}
				class="min-h-0 min-w-0 pointer-events-auto overflow-hidden"
				data-panel-group={tabGroups[tab.id]?.id}
				style={positions.groups[tabGroups[tab.id]?.id]
					? paneStyle(positions.groups[tabGroups[tab.id].id], 36)
					: 'display:none'}
				class:hidden={!visibleTabIds.has(tab.id)}
				on:focusin={() => focusGroup(tabGroups[tab.id].id)}
				on:pointerdown={() => focusGroup(tabGroups[tab.id].id)}
			>
				{#if tab.terminalId && !connection}
					<div
						role="status"
						class="flex h-full items-center justify-center p-4 text-center text-xs text-gray-400 dark:text-gray-500"
					>
						{$i18n.t('Terminal connection unavailable')}
					</div>
				{:else if tab.kind === 'voice'}
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
					<Embeds overlay={dragged} />
				{:else if tab.kind === 'artifacts'}
					<Artifacts overlay={dragged} />
				{:else if tab.kind === 'side'}
					<SideChat
						bind:this={sideViews[tab.id]}
						initialView={owner.transient[`side:${tab.id}`]}
						chatId={tab.chatId ?? ''}
						onChatUpdate={(chat) =>
							updateViewTab(owner, tab.id, {
								chatId: chat.id,
								...(chat.title ? { label: chat.title } : {})
							})}
						parentChatId={owner.chatId ?? ''}
						parentFolderId={folderId}
						{history}
						{modelId}
						{systemPrompt}
						initialPrompt={tab.initialPrompt ?? ''}
					/>
				{:else if tab.kind === 'comments' && currentComments}
					{#key `${$user?.id}:$chatId={owner.chatId}:${currentComments.comment_id ?? ''}`}
						<CommentsPanel
							embedded={true}
							bind:view={currentComments}
							onCountChange={setCommentCount}
						/>
					{/key}
				{:else if tab.kind === 'desktop' && connection}
					<Desktop
						connection={connection!}
						chatId={owner.chatId}
						active={panelVisible && visibleTabIds.has(tab.id)}
						overlay={dragged}
					/>
				{:else if tab.kind === 'browser' || tab.kind === 'terminal'}
					{#if owner.pending.has(tab.id)}
						<p
							role="status"
							class="flex h-full items-center justify-center p-4 text-center text-xs text-gray-400 dark:text-gray-500"
						>
							{$i18n.t('Connecting…')}
						</p>
					{:else if !tab.sessionId || failure}
						<div
							role="status"
							class="flex h-full flex-col items-center justify-center gap-3 p-4 text-center text-xs text-gray-400 dark:text-gray-500"
						>
							<p>
								{failure?.status === 404
									? $i18n.t('Session no longer available')
									: (failure?.message ??
										owner.sessionErrors[tab.id] ??
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
								<button class="underline" on:click={() => startSession(owner, tab)}
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
									connection={connection!}
									chatId={owner.chatId}
									sessionId={tab.sessionId}
									active={panelVisible && visibleTabIds.has(tab.id)}
									overlay={dragged}
									onUnavailable={(message, status) => {
										if (owner === viewEntry)
											sessionFailures = { ...sessionFailures, [tab.id]: { message, status } };
									}}
								/>
							{:else}
								<Browser
									bind:this={browserViews[tab.id]}
									{connection}
									chatId={owner.chatId}
									sessionId={tab.sessionId}
									active={panelVisible && visibleTabIds.has(tab.id)}
									overlay={dragged}
									onOpenBrowser={(url) => openBrowser(undefined, tab.terminalId, undefined, url)}
									onNavigate={(path, label) => updateViewTab(owner, tab.id, { path, label })}
									onUnavailable={(message, status) => {
										if (owner === viewEntry)
											sessionFailures = { ...sessionFailures, [tab.id]: { message, status } };
									}}
								/>
							{/if}
						{/key}
					{/if}
				{:else if tab.untitled && connection}
					<UntitledFile
						initialView={owner.drafts.get(tab.id)}
						bind:this={fileViews[tab.id]}
						bind:dirty={dirtyFiles[tab.id]}
						label={tab.label}
						connection={connection!}
						chatId={owner.chatId}
						initialDirectory={tab.context?.currentDirectory}
						isOpen={(path) =>
							tabs.tabs.some(
								(item) =>
									item.id !== tab.id &&
									item.kind === 'file' &&
									!item.untitled &&
									item.terminalId === tab.terminalId &&
									item.path === path
							)}
						onSaved={(path) => {
							owner.drafts.delete(tab.id);
							updateViewTab(owner, tab.id, {
								untitled: false,
								dirty: false,
								path,
								label: path.split('/').pop() || path
							});
						}}
					/>
				{:else if (tab.kind === 'files' || tab.kind === 'file') && tab.terminalId}
					{@const fileConnection = mounted
						? resolveTerminalConnection(
								tab.terminalId,
								$terminalServers ?? [],
								directTerminals,
								localStorage.token ?? ''
							)
						: null}
					<div class="flex h-full min-h-0 flex-col">
						<div class="min-h-0 flex-1">
							<FileNav
								onFileSaved={(content) => {
									const draft = owner.drafts.get(tab.id);
									if (draft?.preview) {
										draft.preview.baseText = content;
										draft.dirty = draft.preview.dirty = draft.preview.text !== content;
									}
								}}
								initialView={owner.drafts.get(tab.id)}
								onViewChange={(view) => {
									owner.drafts.set(tab.id, view);
									if (tab.kind === 'files')
										updateViewTab(owner, tab.id, {
											directory: view.directory,
											label: view.isHome
												? $i18n.t('Home')
												: view.directory?.split('/').filter(Boolean).pop() || $i18n.t('Files')
										});
								}}
								onFilesMoved={() => {
									if (owner !== viewEntry) return;
									for (const other of tabs.tabs) {
										if (
											other.id !== tab.id &&
											other.kind === 'files' &&
											other.terminalId === tab.terminalId
										)
											void fileViews[other.id]?.refreshDirectory?.();
									}
								}}
								gitStatus={fileGitStatuses[tab.terminalId] ?? null}
								gitConnection={fileConnection}
								gitDiffMode={fileGitDiffModes[tab.terminalId] ?? 'unified'}
								gitHideWhitespace={fileGitHideWhitespace[tab.terminalId] ?? false}
								bind:this={fileViews[tab.id]}
								bind:dirty={dirtyFiles[tab.id]}
								terminalId={tab.terminalId}
								initialFile={tab.kind === 'file' ? { path: tab.path!, page: tab.page } : null}
								initialDirectory={tab.kind === 'files' ? (tab.directory ?? tab.path ?? null) : null}
								active={panelVisible && visibleTabIds.has(tab.id)}
								manageFileRequests={false}
								showTerminalDock={tab.kind === 'files'}
								onOpenFile={(path, page) => openFile(path, tab.terminalId!, page)}
								onBrowseDirectory={(path) => openFiles(tab.terminalId, path)}
								{onAskFile}
								overlay={dragged}
								chatId={owner.chatId}
								bind:terminalContext={fileContexts[tab.id]}
							/>
						</div>
						{#if tab.kind === 'files' && fileConnection}
							<GitBar
								bind:this={gitViews[tab.id]}
								initialView={owner.transient[`git:${tab.id}`]}
								bind:status={fileGitStatuses[tab.terminalId]}
								bind:diffMode={fileGitDiffModes[tab.terminalId]}
								bind:hideWhitespace={fileGitHideWhitespace[tab.terminalId]}
								connection={fileConnection}
								chatId={owner.chatId}
								directory={fileContexts[tab.id]?.currentDirectory ??
									tab.directory ??
									tab.path ??
									'.'}
								active={panelVisible && visibleTabIds.has(tab.id)}
								onOpenFile={(path) => openFile(path, tab.terminalId!)}
								onOpenDirectory={(path) => openFiles(tab.terminalId, path)}
							/>
						{/if}
					</div>
				{:else if tab.kind === 'files' && codeInterpreterEnabled}
					<PyodideFileNav overlay={dragged} />
				{/if}
			</div>
		{/each}
		{#if viewReady && !chatLoading && !viewError && !tabs.tabs.length && canOpenNewTab}<div
				class="flex h-full items-center justify-center p-4 text-center text-xs text-gray-400"
			>
				{$i18n.t('Open a tab using the + menu.')}
			</div>{/if}
	</div>
</div>

{#snippet tabBar(group: PanelGroup)}
	<div
		data-panel-tab-bar
		class="flex h-9 items-center px-1.5 {fullWidth &&
		positions.groups[group.id]?.top === 0 &&
		positions.groups[group.id].left + positions.groups[group.id].width > 0.999
			? 'pr-10'
			: ''} gap-1 shrink-0 pointer-events-auto select-none col-start-1 row-start-1 min-w-0 z-10"
	>
		<div class="flex items-center gap-0.5 flex-1 min-w-0 py-0.5">
			<div
				role="tablist"
				data-swipe-no-gesture
				use:sortableTabs
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
					<div
						role="presentation"
						data-panel-tab={tab.id}
						use:activateFilesOnDrag={tab}
						on:click={() => selectTab(tab.id)}
						class="panel-tab flex cursor-pointer items-center gap-1.5 ps-2.5 pe-2 h-7 rounded-lg text-sm font-normal whitespace-nowrap shrink-0 transition {group.activeId ===
						tab.id
							? 'bg-gray-100/40 dark:bg-gray-800/25 text-gray-700 dark:text-gray-200'
							: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
					>
						<button
							role="tab"
							aria-keyshortcuts={tab.kind === 'chat'
								? undefined
								: 'Alt+Shift+ArrowLeft Alt+Shift+ArrowRight'}
							id={domId(tab.id)}
							aria-controls={`${domId(tab.id)}-view`}
							aria-selected={group.activeId === tab.id}
							tabindex={group.activeId === tab.id ? 0 : -1}
							title={tab.kind === 'chat' ? title : (tab.directory ?? tab.path ?? tab.label)}
							aria-label={tab.kind === 'chat' ? title : undefined}
							class="flex h-full items-center gap-1.5 min-w-0"
						>
							{#if tab.kind === 'file'}
								<Icon name={fileIconName(tab.label)} size={14} strokeWidth={1.4} />
							{:else if tab.kind === 'comments'}
								<Annotation className="size-3.5 shrink-0" />
							{:else}
								<Icon name={tabIcon(tab.kind)} size={14} />
							{/if}
							{#if tab.kind !== 'chat' || !tabTitleEditor}
								<span class="max-w-30 overflow-hidden text-ellipsis"
									>{tab.kind === 'chat' ? title : tab.label}</span
								>
							{/if}
							{#if tab.kind === 'comments' && commentCount}<span class="text-gray-400"
									>{commentCount}</span
								>{/if}
						</button>
						{#if tab.untitled || dirtyFiles[tab.id]}<span
								class="ms-1 size-1.5 shrink-0 rounded-full bg-gray-400"
								aria-label={$i18n.t('Unsaved changes')}
							></span>{/if}
						{#if tab.kind === 'chat'}
							{@render tabTitleEditor?.()}
							{@render tabActions?.()}
						{:else}<button
								type="button"
								class="flex items-center justify-center w-4 h-4 rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700 dark:hover:bg-white/10 dark:hover:text-white"
								title={[
									$i18n.t('Close'),
									$settings?.keyboardShortcuts !== false ? formatChord($keybindings.closeTab) : ''
								]
									.filter(Boolean)
									.join(' · ')}
								aria-label={tab.kind === 'voice'
									? $i18n.t('End call')
									: `${$i18n.t('Close')} ${tab.label}`}
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
						class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 shrink-0"
						aria-label={$i18n.t('New tab')}><Icon name="plus" size={14} /></button
					>
					<div slot="content">
						<DropdownMenu className="min-w-56">
							{#if showFilesTab}
								<button on:click={() => openFiles($selectedTerminalId, undefined, true)}
									><Icon name="folder" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Files')}</span
									><HotkeyHint name="openFiles" className="ms-auto" /></button
								>
							{/if}
							{#if terminalFilesAvailable}<button on:click={newFile}
									><Icon name="page" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('New File')}</span
									><HotkeyHint name="newFile" className="ms-auto" /></button
								>{/if}
							{#if terminalEnabled}<button on:click={newTerminal}
									><Icon name="terminal" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('New Terminal')}</span
									><HotkeyHint name="newTerminal" className="ms-auto" /></button
								>{/if}
							{#if browserEnabled}<button on:click={() => openBrowser()}
									><Icon name="browser" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Browser')}</span
									><HotkeyHint name="newBrowser" className="ms-auto" /></button
								>{/if}
							{#if desktopEnabled}<button on:click={openDesktop}
									><Icon name="monitor" size={14} /><span class="flex-1 text-start"
										>{$i18n.t('Desktop')}</span
									><HotkeyHint name="openDesktop" className="ms-auto" /></button
								>{/if}
							{#if canVoiceNote}
								<button on:click={openVoiceNote}>
									<Icon name="microphone" size={14} />
									<span class="flex-1 text-start">{$i18n.t('Voice Note')}</span>
									<HotkeyHint name="voiceNote" className="ms-auto" />
								</button>
							{/if}
							{#each newTabViews as view}
								<button
									on:click={() =>
										openFeature(
											view.kind as 'artifacts' | 'preview' | 'voice' | 'comments' | 'side'
										)}
								>
									{#if view.kind === 'comments'}
										<Annotation className="size-3.5 shrink-0" />
									{:else}
										<Icon name={tabIcon(view.kind as PanelTab['kind'])} size={14} />
									{/if}<span class="flex-1 text-start">{view.label}</span>
									{#if view.kind === 'side'}
										<HotkeyHint name="newChatTab" className="ms-auto" />
									{:else if view.kind === 'comments'}
										<HotkeyHint name="openComments" className="ms-auto" />
									{/if}
								</button>
							{/each}
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
		{#if !fullWidth && (!largeScreen || group.id === tabs.groups[0].id)}
			<button
				type="button"
				class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 shrink-0"
				on:click={() => showTabs.set(false)}
				aria-label={$i18n.t('Hide tabs')}><Icon name="xmark" size={12} /></button
			>
		{/if}
	</div>
{/snippet}

{#if !largeScreen}
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
				className="min-h-[100dvh] !bg-white dark:!bg-gray-900"
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
