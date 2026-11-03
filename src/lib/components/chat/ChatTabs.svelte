<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import type { GitStatus } from '$lib/apis/terminal/git';
	let gitStatus: GitStatus | null = null;
	let gitDiffMode: 'unified' | 'split' = 'unified';
	let gitHideWhitespace = false;
	import { onMount, onDestroy, tick, getContext } from 'svelte';
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
		mainChatTabId,
		setFullWidthTabs,
		fileTabId,
		type PanelTab
	} from './ChatTabs/tabs';
	import {
		resolveTerminalConnection,
		terminalRequest,
		type TerminalConnection
	} from '$lib/apis/terminal';
	import Dropdown from '../common/Dropdown.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';
	import Icon from './FileNav/Icon.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import { fileIconName } from './FileNav/fileIcon';
	import UntitledFile from './ChatTabs/UntitledFile.svelte';
	import Browser from './ChatTabs/Browser.svelte';
	import Desktop from './ChatTabs/Desktop.svelte';
	import XTerminal from './XTerminal.svelte';
	import CallPanel from './MessageInput/CallPanel.svelte';
	import Drawer from '../common/Drawer.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';
	import GitBar from './ChatTabs/GitBar.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatTabs/Embeds.svelte';
	import SideChat from './ChatTabs/SideChat.svelte';
	import FileNav from './FileNav.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import Overview from './Overview.svelte';
	import Modal from '../common/Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import { isSavedChatId } from '$lib/utils/chatId';

	const i18n = getContext<any>('i18n');

	export let history;

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
	export let files: any[];
	export let modelId;
	export let systemPrompt = '';
	export let canSideChat = false;

	export let codeInterpreterEnabled = false;
	export let fullWidth = false;
	export let mainChatActive = false;
	export let title = '';
	export let tabTitleEditor: import('svelte').Snippet | undefined = undefined;
	export let tabActions: import('svelte').Snippet | undefined = undefined;
	let expanded = false;
	$: fullWidth = expanded && largeScreen && !!$showTabs;
	$: mainChatActive = fullWidth && tabs.activeId === mainChatTabId;
	$: if (fullWidth !== tabs.tabs.some((tab) => tab.id === mainChatTabId)) {
		tabs = setFullWidthTabs(tabs, fullWidth, title);
		if (fullWidth) void tick().then(() => document.getElementById(domId(mainChatTabId))?.focus());
	}
	const toggleLayout = async () => {
		if (panelTarget) releasePanel(panelTarget);
		expanded = !expanded;
		localStorage.setItem('chatTabsLayout', expanded ? 'full' : 'side');
		await tick();
		if (!fullWidth) document.getElementById('chat-tabs-layout-toggle')?.focus();
	};

	let largeScreen = false;
	let dragged = false;
	let mounted = false;
	let controlsWidth = 300;
	let viewportWidth = 0;

	let tabs = emptyTabs();
	let sideChatNumber = 0;
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
				if ($showTabs && panelTarget === destination && destination.isConnected) move(destination);
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
	// Resolve before reactive Files-tab creation, which can run later in the same update.
	$: gitConnection =
		mounted &&
		$config?.features?.enable_tool_servers &&
		(contextTab?.connection ??
			resolveTerminalConnection(
				contextTab?.terminalId ?? $selectedTerminalId,
				$terminalServers ?? [],
				directTerminals,
				localStorage.token ?? ''
			));
	$: if (activeTabId && panelTarget) {
		const id = activeTabId;
		void tick().then(() =>
			document
				.getElementById(domId(id))
				?.parentElement?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
		);
	}

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
			id: crypto.randomUUID(),
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
			const pending = $sideChatRequest;
			const initialPrompt = pending?.parentId === chatId ? pending.prompt : '';
			if (pending?.parentId === chatId) sideChatRequest.set(null);
			openPanel({
				id: crypto.randomUUID(),
				kind,
				label: `${view.label} ${++sideChatNumber}`,
				initialPrompt
			});
			return;
		}
		openPanel({ id: kind, kind, label: view.label });
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
			id: crypto.randomUUID(),
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
			id: crypto.randomUUID(),
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
				dragged = true;
			},
			onEnd: ({
				item,
				from,
				newDraggableIndex
			}: {
				item: HTMLElement;
				from: HTMLElement;
				newDraggableIndex?: number;
			}) => {
				// Restore the DOM before Svelte reconciles its keyed tabs.
				from.insertBefore(item, nextSibling?.parentNode === from ? nextSibling : null);
				if (newDraggableIndex != null)
					tabs = moveTab(tabs, item.dataset.panelTab!, newDraggableIndex + (fullWidth ? 1 : 0));
				dragged = false;
			}
		});
		return { destroy: () => sortable.destroy() };
	};
	const navigateTabs = (event: KeyboardEvent) => {
		if (!(event.target instanceof HTMLElement) || event.target.getAttribute('role') !== 'tab')
			return;
		const index = tabs.tabs.findIndex((tab) => tab.id === tabs.activeId);
		if (event.altKey && event.shiftKey && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
			event.preventDefault();
			tabs = moveTab(tabs, tabs.activeId, index + (event.key === 'ArrowLeft' ? -1 : 1));
			return;
		}
		let next = index;
		if (event.key === 'ArrowRight') next = (index + 1) % tabs.tabs.length;
		else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.tabs.length) % tabs.tabs.length;
		else if (event.key === 'Home') next = 0;
		else if (event.key === 'End') next = tabs.tabs.length - 1;
		else return;
		event.preventDefault();
		selectTab(tabs.tabs[next].id);
		document.getElementById(domId(tabs.tabs[next].id))?.focus();
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
			label: $i18n.t('Side chat'),
			available: canSideChat && !!chatId && hasMessages
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
	const checkTerminal = async () => {
		const version = ++featureVersion;
		terminalEnabled = false;
		desktopEnabled = false;
		browserEnabled = false;
		selectedConnection =
			terminalFilesAvailable && mounted
				? resolveTerminalConnection(
						$selectedTerminalId,
						$terminalServers ?? [],
						directTerminals,
						localStorage.token ?? ''
					)
				: null;
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
		terminalFilesAvailable;
		$selectedTerminalId;
		$terminalServers;
		$settings;
		mounted;
		chatId;
		void checkTerminal();
	}

	$: if (chatId !== tabsChatId) {
		if (tabsChatId || !chatId) {
			tabs = setFullWidthTabs(emptyTabs(), fullWidth, title);
			sideChatNumber = 0;
			hasOpenedTabs = false;
			dirtyFiles = {};
			fileContexts = {};
			commentTarget = {};
		}
		tabsChatId = chatId;
	}
	$: if ($showTabs === true && !tabs.tabs.length) {
		const options = [
			...availableViews
				.filter((view) => view.available)
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
		hasOpenedTabs = true;
	}
	$: if (
		!(
			$user?.role === 'admin' ||
			($user?.role === 'user' &&
				($user.permissions?.chat?.temporary ?? true) &&
				($user.permissions?.chat?.side_chat ?? false))
		) &&
		$sideChatRequest?.parentId === chatId
	)
		sideChatRequest.set(null);
	$: if ($showTabs === 'files' && showFilesTab) openFiles();
	$: if ($showTabs === 'side' && chatId && hasMessages) {
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

	const onPointerDown = (event: PointerEvent) => {
		if (event.target instanceof Element && event.target.closest('#controls-resizer'))
			dragged = true;
	};
	const onPointerUp = () => {
		dragged = false;
	};

	onMount(() => {
		const unsubscribeVisibility = showTabs.subscribe((visible) => {
			if (!visible && panelTarget) releasePanel(panelTarget);
		});
		const mediaQuery = window.matchMedia('(min-width: 768px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
		expanded = localStorage.getItem('chatTabsLayout') === 'full';
		if (expanded && largeScreen && !$showTabs) showTabs.set(true);

		let isDestroyed = false;

		const init = async () => {
			await tick();

			if (isDestroyed) return;

			setTimeout(() => {
				mounted = true;
			}, 0);
		};
		init();

		document.addEventListener('pointerdown', onPointerDown);
		document.addEventListener('pointerup', onPointerUp);
		document.addEventListener('pointercancel', onPointerUp);

		return () => {
			unsubscribeVisibility();
			isDestroyed = true;
			mounted = false;
			if (!largeScreen) {
				showTabs.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
			document.removeEventListener('pointerdown', onPointerDown);
			document.removeEventListener('pointerup', onPointerUp);
			document.removeEventListener('pointercancel', onPointerUp);
		};
	});
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

<div
	class:hidden={!$showTabs || !panelTarget}
	use:placePanel={$showTabs ? panelTarget : null}
	class={fullWidth ? 'contents' : 'h-full w-full min-h-0 flex flex-col'}
	style:--chat-tabs-dark-background={'var(--color-gray-900)'}
	id="controls-container"
>
	<div
		class="flex items-center px-2 pt-1 pb-1 gap-1 shrink-0 select-none col-start-1 row-start-1 min-w-0 z-10 bg-white dark:bg-gray-900"
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
				{#each tabs.tabs as tab (tab.id)}
					<div
						role="presentation"
						data-panel-tab={tab.kind === 'chat' ? undefined : tab.id}
						on:click={() => selectTab(tab.id)}
						class="panel-tab flex cursor-pointer items-center gap-1.5 ps-2.5 pe-2 h-7 rounded-lg text-sm font-normal whitespace-nowrap shrink-0 transition {tabs.activeId ===
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
							aria-selected={tabs.activeId === tab.id}
							tabindex={tabs.activeId === tab.id ? 0 : -1}
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
						<DropdownMenu className="w-48">
							{#if showFilesMenuItem}
								<button on:click={() => openFiles()}
									><Icon name="folder" size={14} />{$i18n.t('Files')}</button
								>
							{/if}
							{#if terminalFilesAvailable}<button on:click={newFile}
									><Icon name="page" size={14} />{$i18n.t('New File')}</button
								>{/if}
							{#if terminalEnabled}<button on:click={newTerminal}
									><Icon name="terminal" size={14} />{$i18n.t('New Terminal')}</button
								>{/if}
							{#if browserEnabled}<button on:click={() => openBrowser()}
									><Icon name="browser" size={14} />{$i18n.t('Browser')}</button
								>{/if}
							{#if desktopEnabled}<button on:click={openDesktop}
									><Icon name="monitor" size={14} />{$i18n.t('Desktop')}</button
								>{/if}
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
									{/if}{view.label}
								</button>
							{/each}
						</DropdownMenu>
					</div>
				</Dropdown>
			{/if}
		</div>
		{#if largeScreen}
			<button
				id="chat-tabs-layout-toggle"
				type="button"
				class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 shrink-0"
				on:click={toggleLayout}
				aria-label={fullWidth ? $i18n.t('Use side tabs') : $i18n.t('Use full-width tabs')}
				title={fullWidth ? $i18n.t('Use side tabs') : $i18n.t('Use full-width tabs')}
				aria-pressed={fullWidth}
			>
				<Icon name={fullWidth ? 'split-horizontal' : 'expand'} size={14} />
			</button>
		{/if}
		{#if !fullWidth}
			<button
				type="button"
				class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 shrink-0"
				on:click={() => showTabs.set(false)}
				aria-label={$i18n.t('Hide tabs')}><Icon name="xmark" size={12} /></button
			>
		{/if}
	</div>
	<div
		class="relative flex-1 min-h-0 min-w-0 col-start-1 row-start-2"
		class:hidden={mainChatActive}
	>
		{#each tabs.tabs.filter((tab) => tab.kind !== 'chat') as tab (tab.id)}
			<div
				id={`${domId(tab.id)}-view`}
				role="tabpanel"
				aria-labelledby={domId(tab.id)}
				class="h-full w-full min-h-0"
				class:hidden={tabs.activeId !== tab.id}
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
				{:else if tab.kind === 'side' && chatId}
					<SideChat {history} {modelId} {systemPrompt} initialPrompt={tab.initialPrompt ?? ''} />
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
						active={!!$showTabs && tabs.activeId === tab.id}
						overlay={dragged}
					/>
				{:else if tab.kind === 'browser'}
					<Browser
						baseUrl={tab.browserBaseUrl ?? ''}
						connection={tab.connection ?? null}
						{chatId}
						active={!!$showTabs && tabs.activeId === tab.id}
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
						active={!!$showTabs && tabs.activeId === tab.id}
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
					<FileNav
						gitStatus={gitConnection && gitConnection.selector === tab.terminalId
							? gitStatus
							: null}
						gitConnection={gitConnection && gitConnection.selector === tab.terminalId
							? gitConnection
							: null}
						{gitDiffMode}
						{gitHideWhitespace}
						bind:this={fileViews[tab.id]}
						bind:dirty={dirtyFiles[tab.id]}
						terminalId={tab.terminalId}
						initialFile={tab.kind === 'file' ? { path: tab.path!, page: tab.page } : null}
						initialDirectory={tab.kind === 'files' ? (tab.path ?? null) : null}
						active={!!$showTabs && tabs.activeId === tab.id}
						manageFileRequests={false}
						showTerminalDock={tab.kind === 'files'}
						onOpenFile={(path, page) => openFile(path, tab.terminalId!, page)}
						onBrowseDirectory={(path) => openFiles(tab.terminalId, path)}
						{onAskFile}
						overlay={dragged}
						{chatId}
						bind:terminalContext={fileContexts[tab.id]}
					/>
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
	<div class="col-start-1 row-start-3 min-w-0" class:hidden={mainChatActive}>
		{#if gitConnection && tabs.tabs.length}
			<GitBar
				bind:status={gitStatus}
				bind:diffMode={gitDiffMode}
				bind:hideWhitespace={gitHideWhitespace}
				connection={gitConnection}
				{chatId}
				directory={terminalContext?.currentDirectory ?? '.'}
				active={!!$showTabs}
				onOpenFile={(path) => openFile(path, gitConnection.selector)}
				onOpenDirectory={(path) => openFiles(gitConnection.selector, path)}
			/>
		{/if}
	</div>
</div>

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
{:else}
	<ResizableSidePanel
		open={!!$showTabs && !fullWidth}
		bind:width={controlsWidth}
		minWidth={280}
		minSiblingWidth={360}
		storageKey="chatControlsSize"
		className="h-full z-10 bg-white dark:bg-gray-900"
	>
		<div
			use:preservePanel
			bind:this={panelTarget}
			class="h-full w-full z-40 pointer-events-auto"
		></div>
	</ResizableSidePanel>
	{#if fullWidth}
		<!-- The tab strip and pane share the parent chat's grid without remounting either view. -->
		<div use:preservePanel bind:this={panelTarget} class="contents"></div>
	{/if}
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
