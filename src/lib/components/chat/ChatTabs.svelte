<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import type { GitStatus } from '$lib/apis/terminal/git';
	let fileGitStatuses: Record<string, GitStatus | null> = {};
	let fileGitDiffModes: Record<string, 'unified' | 'split'> = {};
	let fileGitHideWhitespace: Record<string, boolean> = {};
	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import Sortable from 'sortablejs';
	import { beforeNavigate, goto } from '$app/navigation';
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
		type TerminalConnection
	} from '$lib/apis/terminal';
	import { formatChord, keybindings, matchKeybinding, Shortcut } from '$lib/shortcuts';
	import HotkeyHint from '../common/HotkeyHint.svelte';
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
	import XMark from '../icons/XMark.svelte';
	import SplitPanel from '../icons/SplitPanel.svelte';
	import { isSavedChatId } from '$lib/utils/chatId';

	const i18n = getContext<any>('i18n');

	export let history;

	export let chatId: string | null = null;
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
	$: if (largeScreen !== tabs.tabs.some((tab) => tab.id === mainChatTabId)) {
		tabs = setMainChatTab(tabs, largeScreen, title);
	}

	let largeScreen = false;
	let dragged = false;
	let mounted = false;
	let viewportWidth = 0;

	let tabs = emptyTabs();
	const paneStyle = (rect: PanelRect, header = 0) =>
		`position:absolute;left:${rect.left * 100}%;top:calc(100% * ${rect.top} + ${header}px * var(--app-text-scale, 1));width:${rect.width * 100}%;height:calc(100% * ${rect.height} - ${header}px * var(--app-text-scale, 1));`;
	const focusGroup = (id: string) => {
		const group = tabs.groups.find((group) => group.id === id);
		if (group?.activeId) tabs = activateTab(tabs, group.activeId);
	};
	let terminalViews: Record<string, XTerminal> = {};
	export const hasTerminals = () => tabs.tabs.some((tab) => tab.kind === 'terminal');
	export async function bindTerminalChat(id: string) {
		await tick();
		await Promise.all(
			tabs.tabs
				.filter((tab) => tab.kind === 'terminal')
				.map((tab) => terminalViews[tab.id]?.bindChat(id))
		);
	}
	let fileViews: Record<
		string,
		{
			hasUnsavedChanges: () => boolean;
			requestClose: () => Promise<boolean>;
			browseDirectory?: (path: string) => unknown;
			revealPage?: (page: number | null) => void;
		}
	> = {};
	let dirtyFiles: Record<string, boolean> = {};
	let fileContexts: Record<string, TerminalContext | null> = {};
	let panelTarget: HTMLElement | null = null;
	let tabsChatId = chatId;
	let hasOpenedTabs = false;
	let commentTarget: { comment_id?: string } = {};
	let closing = new Set<string>();
	let navigationApproved = false;
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
	$: terminalContext = (contextTab && fileContexts[contextTab.id]) ?? contextTab?.context ?? null;
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
	const openPanel = (tab: PanelTab) => {
		hasOpenedTabs = true;
		tabs = openTab(tabs, tab);
		showTabs.set(true);
	};
	const openFiles = (selector = $selectedTerminalId, directory?: string) => {
		if (selector ? !terminalAccessible(selector) : !showFilesTab) return;
		const id = selector ? `files:${selector}` : 'files';
		openPanel({
			id,
			kind: 'files',
			label: $i18n.t('Files'),
			terminalId: selector ?? undefined,
			path: directory
		});
		if (directory) void fileViews[id]?.browseDirectory?.(directory);
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
	const openFeature = (kind: 'artifacts' | 'preview' | 'voice' | 'comments' | 'side') => {
		if (!availableViews.some((view) => view.kind === kind && view.available)) return;
		const view = availableViews.find((view) => view.kind === kind)!;
		if (kind === 'side') {
			let sideChatNumber = 1;
			while (tabs.tabs.some((tab) => tab.kind === 'side' && tab.sideChatNumber === sideChatNumber))
				sideChatNumber++;
			const pending = $sideChatRequest;
			const initialPrompt = pending?.parentId === chatId ? pending.prompt : '';
			if (pending?.parentId === chatId) sideChatRequest.set(null);
			openPanel({
				id: uuidv4(),
				kind,
				label: `${view.label} ${sideChatNumber}`,
				sideChatNumber,
				initialPrompt
			});
			return;
		}
		openPanel({ id: kind, kind, label: view.label });
	};
	const updateSideChat = (tabId: string, chat: { id: string; title?: string }) => {
		tabs = {
			...tabs,
			tabs: tabs.tabs.map((tab) =>
				tab.id === tabId ? { ...tab, chatId: chat.id, label: chat.title || tab.label } : tab
			)
		};
	};
	type SplitDrop = PanelRect & { groupId: string; edge: SplitEdge | null };
	let chatDropPreview: SplitDrop | null = null;
	let draggedTabId = '';
	let pendingTabDrop: (() => void) | null = null;
	const clearChatDropPreview = () => (chatDropPreview = null);
	const canDropChat = (event: DragEvent) =>
		canSideChat &&
		($user?.role === 'admin' || !($user?.permissions?.chat?.temporary_enforced ?? false)) &&
		event.dataTransfer?.types.includes('application/x-open-webui-chat');
	const chatDropBounds = (event: DragEvent): SplitDrop | null => {
		const internal = event.dataTransfer?.types.includes('application/x-chat-panel-tab');
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
		openPanel({
			id: uuidv4(),
			kind: 'terminal',
			label: `${$i18n.t('Terminal')} ${terminalNumber}`,
			terminalNumber,
			terminalId: selectedConnection.selector,
			connection: { ...selectedConnection }
		});
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
		openPanel({
			id: uuidv4(),
			kind: 'browser',
			label: port ? `localhost:${port}` : $i18n.t('Browser'),
			path: url,
			terminalId: selector ?? undefined,
			browserBaseUrl: proxyBase,
			connection: connection ?? undefined
		});
	};
	const closeTab = async (id: string) => {
		if (id === mainChatTabId) return;
		if (closing.has(id)) return;
		closing.add(id);
		try {
			const tab = tabs.tabs.find((item) => item.id === id);
			if (!tab) return;
			if (fileViews[id]?.hasUnsavedChanges()) {
				selectTab(id);
				if (!(await fileViews[id].requestClose())) return;
			}
			if (tab.kind === 'voice') {
				bridge?.end();
				showCallOverlay.set(false);
			}
			if (tab.kind === 'artifacts') showArtifacts.set(false);
			if (tab.kind === 'preview') showEmbeds.set(false);
			tabs = removeTab(tabs, id);
			delete dirtyFiles[id];
			delete fileContexts[id];
			if (!tabs.tabs.length) showTabs.set(false);
			await tick();
			document.getElementById(domId(tabs.activeId))?.focus();
		} finally {
			closing.delete(id);
		}
	};
	let tabDropHandled = false;
	const sortableTabs = (node: HTMLElement) => {
		let nextSibling: ChildNode | null = null;
		const sortable = new Sortable(node, {
			animation: 150,
			direction: 'horizontal',
			draggable: '[data-panel-tab]',
			handle: '[role="tab"]',
			delay: 200,
			delayOnTouchOnly: true,
			touchStartThreshold: 5,
			ghostClass: 'opacity-40',
			setData: (transfer: DataTransfer, item: HTMLElement) =>
				transfer.setData('application/x-chat-panel-tab', item.dataset.panelTab ?? ''),
			onStart: ({ item }: { item: HTMLElement }) => {
				nextSibling = item.nextSibling;
				tabDropHandled = false;
				draggedTabId = item.dataset.panelTab ?? '';
				dragged = true;
			},
			onEnd: ({ item, from }: { item: HTMLElement; from: HTMLElement }) => {
				const id = item.dataset.panelTab!;
				const group = tabGroups[id];
				const order = Array.from(from.querySelectorAll<HTMLElement>('[data-panel-tab]'))
					.map((tab) => tab.dataset.panelTab!)
					.filter((tabId) => group?.tabIds.includes(tabId));
				// Restore the DOM before Svelte reconciles its keyed tabs.
				from.insertBefore(item, nextSibling?.parentNode === from ? nextSibling : null);
				if (!tabDropHandled) tabs = moveTab(tabs, id, order.indexOf(id));
				const drop = pendingTabDrop;
				pendingTabDrop = null;
				drop?.();
				draggedTabId = '';
				dragged = false;
			}
		});
		return { destroy: () => sortable.destroy() };
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

	$: showFilesMenuItem =
		showFilesTab &&
		!tabs.tabs.some(
			(tab) => tab.id === ($selectedTerminalId ? `files:${$selectedTerminalId}` : 'files')
		);
	$: newTabViews = availableViews.filter(
		(view) => view.kind !== 'files' && view.kind !== 'voice' && view.available
	);
	$: canOpenNewTab = showFilesMenuItem || terminalFilesAvailable || newTabViews.length > 0;

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
	const pruneTabs = () => {
		const hadTabs = tabs.tabs.length > 0;
		for (const tab of tabs.tabs) {
			// An open side chat owns its model and context; changing the parent must not discard it.
			if (tab.kind === 'side' || tab.kind === 'chat') continue;
			const available = tab.terminalId
				? !!$selectedTerminalId && terminalAccessible(tab.terminalId)
				: availableViews.some((view) => view.kind === tab.kind && view.available);
			if (!available) {
				tabs = removeTab(tabs, tab.id);
				delete dirtyFiles[tab.id];
				delete fileContexts[tab.id];
			}
		}
		if (hadTabs && !tabs.tabs.length) showTabs.set(false);
	};
	$: {
		availableViews;
		$selectedTerminalId;
		$terminalServers;
		$settings;
		$config;
		$user;
		chatId;
		pruneTabs();
	}
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

	$: if (chatId !== tabsChatId) {
		if (tabsChatId || !chatId) {
			tabs = setMainChatTab(emptyTabs(), largeScreen, title);
			hasOpenedTabs = false;
			dirtyFiles = {};
			fileContexts = {};
			fileGitStatuses = {};
			fileGitDiffModes = {};
			fileGitHideWhitespace = {};
			commentTarget = {};
		}
		tabsChatId = chatId;
	}
	$: if (
		mounted &&
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
	$: if ($showTabs === 'side') {
		if (canSideChat) openFeature('side');
		else sideChatRequest.set(null);
		showTabs.set(tabs.tabs.length > 0);
	}
	$: if (
		($showTabs === 'comments' || (typeof $showTabs === 'object' && $showTabs)) &&
		showCommentsTab
	) {
		commentTarget = typeof $showTabs === 'object' ? $showTabs : {};
		openFeature('comments');
	}
	$: if ($showArtifacts && showArtifactsTab) {
		openFeature('artifacts');
		showArtifacts.set(false);
	}
	$: if ($showEmbeds && showPreviewTab) {
		openFeature('preview');
		showEmbeds.set(false);
	}
	$: if ($showCallOverlay) openFeature('voice');
	$: if ($showFileNavPath && terminalFilesAvailable && $selectedTerminalId) {
		const request = $showFileNavPath;
		showFileNavPath.set(null);
		openFile(
			typeof request === 'string' ? request : request.path,
			$selectedTerminalId,
			typeof request === 'string' ? null : request.page
		);
	}

	beforeNavigate(({ from, to, cancel, willUnload }) => {
		if (navigationApproved || from?.url.pathname === to?.url.pathname) return;
		showOverview.set(false);
		const dirtyTabs = tabs.tabs.filter((tab) => fileViews[tab.id]?.hasUnsavedChanges());
		if (!dirtyTabs.length) return;
		cancel();
		if (willUnload || !to) return;
		void (async () => {
			for (const tab of dirtyTabs) {
				selectTab(tab.id);
				if (!(await fileViews[tab.id].requestClose())) return;
			}
			navigationApproved = true;
			try {
				await goto(to.url);
			} finally {
				navigationApproved = false;
			}
		})();
	});
	onDestroy(() => {
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
	$: positions = fullWidth
		? panelPositions(tabs.layout)
		: {
				groups: { [tabs.activeGroupId]: { left: 0, top: 0, width: 1, height: 1 } },
				dividers: []
			};
	$: tabGroups = Object.fromEntries(
		tabs.groups.flatMap((group) => group.tabIds.map((id) => [id, group]))
	);
	$: visibleTabIds = new Set(
		tabs.groups
			.filter((group) => fullWidth || group.id === tabs.activeGroupId)
			.map((group) => group.activeId)
	);
	$: mainChatActive = fullWidth && visibleTabIds.has(mainChatTabId);
	$: mainChatGroupId = tabs.groups.find((group) => group.tabIds.includes(mainChatTabId))?.id ?? '';
	$: mainChatStyle =
		fullWidth && positions.groups[mainChatGroupId]
			? paneStyle(positions.groups[mainChatGroupId], 36)
			: '';
</script>

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
		{#if fullWidth}
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
		{#each tabs.groups.filter((group) => fullWidth || group.id === tabs.activeGroupId) as group (group.id)}
			<div
				data-panel-group={group.id}
				role="presentation"
				class="absolute min-h-0 min-w-0 pointer-events-none flex flex-col overflow-hidden"
				style={paneStyle(positions.groups[group.id])}
				on:focusin={() => focusGroup(group.id)}
				on:pointerdown={() => focusGroup(group.id)}
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
		{#each tabs.tabs.filter((tab) => tab.kind !== 'chat') as tab (tab.id)}
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
				{#if tab.kind === 'voice'}
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
						chatId={tab.chatId ?? ''}
						onChatUpdate={(chat) => updateSideChat(tab.id, chat)}
						parentChatId={chatId ?? ''}
						parentFolderId={folderId}
						{history}
						{modelId}
						{systemPrompt}
						initialPrompt={tab.initialPrompt ?? ''}
					/>
				{:else if tab.kind === 'comments' && currentComments}
					{#key `${$user?.id}:${chatId}:${currentComments.comment_id ?? ''}`}
						<CommentsPanel
							embedded={true}
							bind:view={currentComments}
							onCountChange={setCommentCount}
						/>
					{/key}
				{:else if tab.kind === 'desktop' && tab.connection}
					<Desktop
						connection={tab.connection}
						{chatId}
						active={panelVisible && visibleTabIds.has(tab.id)}
						overlay={dragged}
					/>
				{:else if tab.kind === 'browser'}
					<Browser
						baseUrl={tab.browserBaseUrl ?? ''}
						connection={tab.connection ?? null}
						{chatId}
						active={panelVisible && visibleTabIds.has(tab.id)}
						initialUrl={tab.path ?? ''}
						onOpenBrowser={(url) => openBrowser(undefined, tab.terminalId, tab.browserBaseUrl, url)}
						overlay={dragged}
						onNavigate={(path, label) => {
							tabs = {
								...tabs,
								tabs: tabs.tabs.map((item) =>
									item.id === tab.id ? { ...item, path, label } : item
								)
							};
						}}
					/>
				{:else if tab.kind === 'terminal' && tab.connection}
					<XTerminal
						bind:this={terminalViews[tab.id]}
						connection={tab.connection}
						{chatId}
						active={panelVisible && visibleTabIds.has(tab.id)}
						overlay={dragged}
					/>
				{:else if tab.untitled && tab.connection}
					<UntitledFile
						bind:this={fileViews[tab.id]}
						bind:dirty={dirtyFiles[tab.id]}
						label={tab.label}
						connection={tab.connection}
						{chatId}
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
							tabs = {
								...tabs,
								tabs: tabs.tabs.map((item) =>
									item.id === tab.id
										? {
												...item,
												untitled: false,
												dirty: false,
												path,
												label: path.split('/').pop() || path
											}
										: item
								)
							};
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
								gitStatus={fileGitStatuses[tab.terminalId] ?? null}
								gitConnection={fileConnection}
								gitDiffMode={fileGitDiffModes[tab.terminalId] ?? 'unified'}
								gitHideWhitespace={fileGitHideWhitespace[tab.terminalId] ?? false}
								bind:this={fileViews[tab.id]}
								bind:dirty={dirtyFiles[tab.id]}
								terminalId={tab.terminalId}
								initialFile={tab.kind === 'file' ? { path: tab.path!, page: tab.page } : null}
								initialDirectory={tab.kind === 'files' ? (tab.path ?? null) : null}
								active={panelVisible && visibleTabIds.has(tab.id)}
								manageFileRequests={false}
								showTerminalDock={tab.kind === 'files'}
								onOpenFile={(path, page) => openFile(path, tab.terminalId!, page)}
								onBrowseDirectory={(path) => openFiles(tab.terminalId, path)}
								{onAskFile}
								overlay={dragged}
								{chatId}
								bind:terminalContext={fileContexts[tab.id]}
							/>
						</div>
						{#if tab.kind === 'files' && fileConnection}
							<GitBar
								bind:status={fileGitStatuses[tab.terminalId]}
								bind:diffMode={fileGitDiffModes[tab.terminalId]}
								bind:hideWhitespace={fileGitHideWhitespace[tab.terminalId]}
								connection={fileConnection}
								{chatId}
								directory={fileContexts[tab.id]?.currentDirectory ?? tab.path ?? '.'}
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
		{#if !tabs.tabs.length && canOpenNewTab}<div
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
							title={tab.kind === 'chat' ? title : (tab.path ?? tab.label)}
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
			{#if canOpenNewTab}
				<Dropdown align="start" closeOnSelect>
					<button
						type="button"
						class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 shrink-0"
						aria-label={$i18n.t('New tab')}><Icon name="plus" size={14} /></button
					>
					<div slot="content">
						<DropdownMenu className="min-w-56">
							{#if showFilesMenuItem}
								<button on:click={() => openFiles()}
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
