import { v4 as uuidv4 } from 'uuid';
import type { TerminalContext } from '$lib/types';
import type { TerminalTarget } from '$lib/apis/terminal';

export type TabKind =
	| 'chat'
	| 'page'
	| 'files'
	| 'file'
	| 'terminal'
	| 'browser'
	| 'desktop'
	| 'artifacts'
	| 'preview'
	| 'voice'
	| 'comments'
	| 'overview';
export type Tab = {
	id: string;
	kind: TabKind;
	label: string;
	href?: string;
	initialPrompt?: string;
	chatId?: string;
	chatNumber?: number;
	/** Set only when a new conversation explicitly inherits another chat's context. */
	parentChatId?: string;
	/** For an artifacts tab: the tab of the chat whose artifacts it shows. */
	sourceTabId?: string;
	terminalId?: string;
	terminalNumber?: number;
	path?: string;
	page?: number | null;
	sessionId?: string;
	directory?: string;
	dirty?: boolean;
	untitled?: boolean;
	target?: TerminalTarget;
	browserBaseUrl?: string;
	context?: TerminalContext | null;
};
export type TabGroup = { id: string; tabIds: string[]; activeId: string };
export type SplitEdge = 'left' | 'right' | 'top' | 'bottom';
export type TabLayout =
	| { type: 'group'; groupId: string }
	| {
			type: 'split';
			id: string;
			direction: 'horizontal' | 'vertical';
			ratio: number;
			first: TabLayout;
			second: TabLayout;
	  };
export type TabsState = {
	tabs: Tab[];
	activeId: string;
	history: string[];
	groups: TabGroup[];
	activeGroupId: string;
	layout: TabLayout;
};
export type ChatViewState = {
	schemaVersion: 1;
	selectedTerminalId: string | null;
	panels: TabsState;
};
export type GroupRect = { left: number; top: number; width: number; height: number };
export type SplitDivider = GroupRect & {
	id: string;
	direction: 'horizontal' | 'vertical';
	ratio: number;
};

export const createTabsState = (): TabsState => ({
	tabs: [],
	activeId: '',
	history: [],
	groups: [{ id: 'default', tabIds: [], activeId: '' }],
	activeGroupId: 'default',
	layout: { type: 'group', groupId: 'default' }
});
export const mainChatTabId = 'main-chat';

/** Read layouts saved before all conversation tabs used kind: 'chat'. */
export function normalizeChatTab(
	tab: Omit<Tab, 'kind'> & {
		kind: TabKind | 'side';
		sideChatNumber?: number;
		sideChat?: boolean;
	},
	parentChatId: string | null
): Tab {
	const { sideChatNumber, sideChat, ...current } = tab;
	return {
		...current,
		kind: current.kind === 'side' ? 'chat' : current.kind,
		chatNumber: current.chatNumber ?? sideChatNumber,
		parentChatId:
			current.parentChatId ??
			(current.kind === 'side' && (sideChat ?? (!current.href && !!sideChatNumber))
				? (parentChatId ?? undefined)
				: undefined)
	};
}

export function setMainChatTab(state: TabsState, visible: boolean, label = 'Chat'): TabsState {
	if (!visible) {
		return setSplitTabs(removeTab(state, mainChatTabId), false);
	}
	if (state.tabs.some((tab) => tab.id === mainChatTabId)) return state;
	const groupId = state.activeGroupId;
	const next = {
		...state,
		tabs: [{ id: mainChatTabId, kind: 'chat' as const, label }, ...state.tabs],
		groups: state.groups.map((group) =>
			group.id === groupId
				? {
						...group,
						tabIds: [mainChatTabId, ...group.tabIds],
						activeId: group.activeId || mainChatTabId
					}
				: group
		)
	};
	return activateTab(next, state.activeId || mainChatTabId);
}

export function setSplitTabs(state: TabsState, split: boolean): TabsState {
	if (!split) {
		if (state.groups.length === 1) return state;
		return {
			...state,
			groups: [
				{
					id: state.activeGroupId,
					tabIds: state.groups.flatMap((group) => group.tabIds),
					activeId: state.activeId
				}
			],
			layout: { type: 'group', groupId: state.activeGroupId }
		};
	}
	const group = state.groups.find((group) => group.tabIds.includes(mainChatTabId));
	if (!group || group.tabIds.length < 2) return state;
	return activateTab(splitTab(state, mainChatTabId, group.id, 'left'), state.activeId);
}

export function activateTab(state: TabsState, id: string): TabsState {
	const group = state.groups.find((group) => group.tabIds.includes(id));
	if (!group || (state.activeId === id && group.activeId === id)) return state;
	return {
		...state,
		activeId: id,
		activeGroupId: group.id,
		groups: state.groups.map((item) => (item.id === group.id ? { ...item, activeId: id } : item)),
		history: [
			...state.history.filter((entry) => entry !== id && entry !== state.activeId),
			state.activeId
		].filter(Boolean)
	};
}

export function openTab(state: TabsState, tab: Tab): TabsState {
	return activateTab(
		state.tabs.some((item) => item.id === tab.id)
			? state
			: {
					...state,
					tabs: [...state.tabs, tab],
					groups: state.groups.map((group) =>
						group.id === state.activeGroupId
							? { ...group, tabIds: [...group.tabIds, tab.id] }
							: group
					)
				},
		tab.id
	);
}

/** Opens `tab` in a group beside the one holding `besideId`, so both stay in view. */
export function openTabInSplit(state: TabsState, tab: Tab, besideId = mainChatTabId): TabsState {
	const besideGroup = state.groups.find((group) => group.tabIds.includes(besideId));
	if (!besideGroup) return openTab(state, tab);
	if (state.tabs.some((item) => item.id === tab.id) && !besideGroup.tabIds.includes(tab.id))
		return activateTab(state, tab.id);
	const sideGroup =
		state.groups.find((group) => group.id === state.activeGroupId && group.id !== besideGroup.id) ??
		state.groups.find((group) => group.id !== besideGroup.id);
	const next = openTab(activateTab(state, besideId), tab);
	return sideGroup
		? moveTabToGroup(next, tab.id, sideGroup.id)
		: splitTab(next, tab.id, besideGroup.id, 'right');
}

function removeLayoutGroup(layout: TabLayout, groupId: string): TabLayout | null {
	if (layout.type === 'group') return layout.groupId === groupId ? null : layout;
	const first = removeLayoutGroup(layout.first, groupId);
	const second = removeLayoutGroup(layout.second, groupId);
	return first && second ? { ...layout, first, second } : (first ?? second);
}

function removeFromGroup(state: TabsState, id: string): TabsState {
	const source = state.groups.find((group) => group.tabIds.includes(id));
	if (!source) return state;
	const tabIds = source.tabIds.filter((tabId) => tabId !== id);
	const activeId =
		source.activeId === id
			? ([...state.history].reverse().find((tabId) => tabIds.includes(tabId)) ??
				tabIds[Math.max(0, source.tabIds.indexOf(id) - 1)] ??
				'')
			: source.activeId;
	const groups =
		tabIds.length || state.groups.length === 1
			? state.groups.map((group) =>
					group.id === source.id ? { ...group, tabIds, activeId } : group
				)
			: state.groups.filter((group) => group.id !== source.id);
	const activeGroup = groups.find((group) => group.id === state.activeGroupId) ?? groups[0];
	return {
		...state,
		groups,
		activeGroupId: activeGroup.id,
		activeId: activeGroup.activeId,
		layout: groups.some((group) => group.id === source.id)
			? state.layout
			: removeLayoutGroup(state.layout, source.id)!,
		history: state.history.filter((entry) => entry !== id)
	};
}

export function removeTab(state: TabsState, id: string): TabsState {
	if (!state.tabs.some((tab) => tab.id === id)) return state;
	return { ...removeFromGroup(state, id), tabs: state.tabs.filter((tab) => tab.id !== id) };
}

export function moveTab(state: TabsState, id: string, to: number): TabsState {
	const group = state.groups.find((group) => group.tabIds.includes(id));
	if (!group) return state;
	const from = group.tabIds.indexOf(id);
	if (to < 0 || to >= group.tabIds.length || from === to) return state;
	const tabIds = [...group.tabIds];
	tabIds.splice(to, 0, tabIds.splice(from, 1)[0]);
	return {
		...state,
		groups: state.groups.map((item) => (item.id === group.id ? { ...item, tabIds } : item))
	};
}

export function moveTabToGroup(state: TabsState, id: string, groupId: string): TabsState {
	const target = state.groups.find((group) => group.id === groupId);
	if (!target || !state.tabs.some((tab) => tab.id === id)) return state;
	if (target.tabIds.includes(id)) return activateTab(state, id);
	const next = removeFromGroup(state, id);
	return activateTab(
		{
			...next,
			groups: next.groups.map((group) =>
				group.id === groupId ? { ...group, tabIds: [...group.tabIds, id] } : group
			)
		},
		id
	);
}

export function splitTab(
	state: TabsState,
	id: string,
	groupId: string,
	edge: SplitEdge
): TabsState {
	const source = state.groups.find((group) => group.tabIds.includes(id));
	if (!source || !state.groups.some((group) => group.id === groupId)) return state;
	if (source.id === groupId && source.tabIds.length === 1) return state;
	const next = removeFromGroup(state, id);
	const newGroup: TabGroup = { id: uuidv4(), tabIds: [id], activeId: id };
	const replace = (layout: TabLayout): TabLayout => {
		if (layout.type === 'group') {
			if (layout.groupId !== groupId) return layout;
			const leaf: TabLayout = { type: 'group', groupId: newGroup.id };
			const before = edge === 'left' || edge === 'top';
			return {
				type: 'split',
				id: uuidv4(),
				direction: edge === 'left' || edge === 'right' ? 'horizontal' : 'vertical',
				ratio: 0.5,
				first: before ? leaf : layout,
				second: before ? layout : leaf
			};
		}
		return { ...layout, first: replace(layout.first), second: replace(layout.second) };
	};
	return activateTab(
		{ ...next, groups: [...next.groups, newGroup], layout: replace(next.layout) },
		id
	);
}

export function resizeSplit(layout: TabLayout, id: string, ratio: number): TabLayout {
	if (layout.type === 'group') return layout;
	if (layout.id === id) return { ...layout, ratio: Math.max(0.2, Math.min(0.8, ratio)) };
	return {
		...layout,
		first: resizeSplit(layout.first, id, ratio),
		second: resizeSplit(layout.second, id, ratio)
	};
}

// Flat positions keep every tab view mounted when the split tree changes.
export function getLayoutRects(layout: TabLayout) {
	const groups: Record<string, GroupRect> = {};
	const dividers: SplitDivider[] = [];
	const visit = (node: TabLayout, rect: GroupRect) => {
		if (node.type === 'group') {
			groups[node.groupId] = rect;
			return;
		}
		dividers.push({ ...rect, id: node.id, direction: node.direction, ratio: node.ratio });
		if (node.direction === 'horizontal') {
			visit(node.first, { ...rect, width: rect.width * node.ratio });
			visit(node.second, {
				...rect,
				left: rect.left + rect.width * node.ratio,
				width: rect.width * (1 - node.ratio)
			});
		} else {
			visit(node.first, { ...rect, height: rect.height * node.ratio });
			visit(node.second, {
				...rect,
				top: rect.top + rect.height * node.ratio,
				height: rect.height * (1 - node.ratio)
			});
		}
	};
	visit(layout, { left: 0, top: 0, width: 1, height: 1 });
	return { groups, dividers };
}

export const fileTabId = (terminalId: string, path: string) =>
	JSON.stringify(['file', terminalId, path]);

// Queries selecting an editor resource identify a tab; view queries stay within it.
export function pageTabKey(url: URL): string | null {
	if (url.pathname.startsWith('/workspace/functions')) return null;
	if (
		!/^\/(?:$|c\/|channels\/|notes(?:\/|$)|automations(?:\/|$)|calendar(?:\/|$)|workspace(?:\/|$)|playground(?:\/|$)|home(?:\/|$))/.test(
			url.pathname
		)
	)
		return null;
	const path = url.pathname.replace(/\/$/, '') || '/';
	const id = path.endsWith('/edit') ? url.searchParams.get('id') : null;
	return path + (path === '/' ? url.search : id ? `?id=${encodeURIComponent(id)}` : '');
}
