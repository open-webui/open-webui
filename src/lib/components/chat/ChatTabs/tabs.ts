import { v4 as uuidv4 } from 'uuid';
import type { TerminalContext } from '$lib/types';
import type { TerminalConnection } from '$lib/apis/terminal';

export type PanelTabKind =
	| 'chat'
	| 'files'
	| 'file'
	| 'terminal'
	| 'browser'
	| 'desktop'
	| 'artifacts'
	| 'preview'
	| 'voice'
	| 'comments'
	| 'side';
export type PanelTab = {
	id: string;
	kind: PanelTabKind;
	label: string;
	initialPrompt?: string;
	chatId?: string;
	sideChatNumber?: number;
	terminalId?: string;
	terminalNumber?: number;
	path?: string;
	page?: number | null;
	sessionId?: string;
	directory?: string;
	dirty?: boolean;
	untitled?: boolean;
	connection?: TerminalConnection;
	browserBaseUrl?: string;
	context?: TerminalContext | null;
};
export type PanelGroup = { id: string; tabIds: string[]; activeId: string };
export type SplitEdge = 'left' | 'right' | 'top' | 'bottom';
export type PanelLayout =
	| { type: 'group'; groupId: string }
	| {
			type: 'split';
			id: string;
			direction: 'horizontal' | 'vertical';
			ratio: number;
			first: PanelLayout;
			second: PanelLayout;
	  };
export type PanelTabs = {
	tabs: PanelTab[];
	activeId: string;
	history: string[];
	groups: PanelGroup[];
	activeGroupId: string;
	layout: PanelLayout;
};
export type ChatViewState = {
	schemaVersion: 1;
	selectedTerminalId: string | null;
	panels: PanelTabs;
};
export type PanelRect = { left: number; top: number; width: number; height: number };
export type PanelDivider = PanelRect & {
	id: string;
	direction: 'horizontal' | 'vertical';
	ratio: number;
};

export const emptyTabs = (): PanelTabs => ({
	tabs: [],
	activeId: '',
	history: [],
	groups: [{ id: 'default', tabIds: [], activeId: '' }],
	activeGroupId: 'default',
	layout: { type: 'group', groupId: 'default' }
});
export const mainChatTabId = 'main-chat';

export function setMainChatTab(state: PanelTabs, visible: boolean, label = 'Chat'): PanelTabs {
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

export function setSplitTabs(state: PanelTabs, split: boolean): PanelTabs {
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

export function activateTab(state: PanelTabs, id: string): PanelTabs {
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

export function openTab(state: PanelTabs, tab: PanelTab): PanelTabs {
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

export function openTabInSidePanel(state: PanelTabs, tab: PanelTab): PanelTabs {
	const mainGroup = state.groups.find((group) => group.tabIds.includes(mainChatTabId));
	if (!mainGroup) return openTab(state, tab);
	if (state.tabs.some((item) => item.id === tab.id) && !mainGroup.tabIds.includes(tab.id))
		return activateTab(state, tab.id);
	const sideGroup =
		state.groups.find((group) => group.id === state.activeGroupId && group.id !== mainGroup.id) ??
		state.groups.find((group) => group.id !== mainGroup.id);
	const next = openTab(activateTab(state, mainChatTabId), tab);
	return sideGroup
		? moveTabToGroup(next, tab.id, sideGroup.id)
		: splitTab(next, tab.id, mainGroup.id, 'right');
}

function removeLayoutGroup(layout: PanelLayout, groupId: string): PanelLayout | null {
	if (layout.type === 'group') return layout.groupId === groupId ? null : layout;
	const first = removeLayoutGroup(layout.first, groupId);
	const second = removeLayoutGroup(layout.second, groupId);
	return first && second ? { ...layout, first, second } : (first ?? second);
}

function removeFromGroup(state: PanelTabs, id: string): PanelTabs {
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

export function removeTab(state: PanelTabs, id: string): PanelTabs {
	if (!state.tabs.some((tab) => tab.id === id)) return state;
	return { ...removeFromGroup(state, id), tabs: state.tabs.filter((tab) => tab.id !== id) };
}

export function moveTab(state: PanelTabs, id: string, to: number): PanelTabs {
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

export function moveTabToGroup(state: PanelTabs, id: string, groupId: string): PanelTabs {
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
	state: PanelTabs,
	id: string,
	groupId: string,
	edge: SplitEdge
): PanelTabs {
	const source = state.groups.find((group) => group.tabIds.includes(id));
	if (!source || !state.groups.some((group) => group.id === groupId)) return state;
	if (source.id === groupId && source.tabIds.length === 1) return state;
	const next = removeFromGroup(state, id);
	const newGroup: PanelGroup = { id: uuidv4(), tabIds: [id], activeId: id };
	const replace = (layout: PanelLayout): PanelLayout => {
		if (layout.type === 'group') {
			if (layout.groupId !== groupId) return layout;
			const leaf: PanelLayout = { type: 'group', groupId: newGroup.id };
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

export function resizeSplit(layout: PanelLayout, id: string, ratio: number): PanelLayout {
	if (layout.type === 'group') return layout;
	if (layout.id === id) return { ...layout, ratio: Math.max(0.2, Math.min(0.8, ratio)) };
	return {
		...layout,
		first: resizeSplit(layout.first, id, ratio),
		second: resizeSplit(layout.second, id, ratio)
	};
}

// Flat positions keep every tab view mounted when the split tree changes.
export function panelPositions(layout: PanelLayout) {
	const groups: Record<string, PanelRect> = {};
	const dividers: PanelDivider[] = [];
	const visit = (node: PanelLayout, rect: PanelRect) => {
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
