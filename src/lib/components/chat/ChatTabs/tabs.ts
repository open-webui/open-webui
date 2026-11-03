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
	terminalId?: string;
	terminalNumber?: number;
	path?: string;
	page?: number | null;
	dirty?: boolean;
	untitled?: boolean;
	connection?: TerminalConnection;
	browserBaseUrl?: string;
	context?: TerminalContext | null;
};
export type PanelTabs = { tabs: PanelTab[]; activeId: string; history: string[] };

export const emptyTabs = (): PanelTabs => ({ tabs: [], activeId: '', history: [] });

export const mainChatTabId = 'main-chat';

export function setFullWidthTabs(state: PanelTabs, fullWidth: boolean, label = 'Chat'): PanelTabs {
	if (!fullWidth) return removeTab(state, mainChatTabId);
	if (state.tabs.some((tab) => tab.id === mainChatTabId)) return state;
	return activateTab(
		{ ...state, tabs: [{ id: mainChatTabId, kind: 'chat', label }, ...state.tabs] },
		mainChatTabId
	);
}

export function activateTab(state: PanelTabs, id: string): PanelTabs {
	if (!state.tabs.some((tab) => tab.id === id) || state.activeId === id) return state;
	return {
		...state,
		activeId: id,
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
			: { ...state, tabs: [...state.tabs, tab] },
		tab.id
	);
}

export function removeTab(state: PanelTabs, id: string): PanelTabs {
	const tabs = state.tabs.filter((tab) => tab.id !== id);
	const history = state.history.filter(
		(entry) => entry !== id && tabs.some((tab) => tab.id === entry)
	);
	const index = state.tabs.findIndex((tab) => tab.id === id);
	return {
		tabs,
		activeId:
			state.activeId === id
				? (history.at(-1) ?? tabs[Math.max(0, index - 1)]?.id ?? '')
				: state.activeId,
		history
	};
}

export function moveTab(state: PanelTabs, id: string, to: number): PanelTabs {
	const from = state.tabs.findIndex((tab) => tab.id === id);
	if (id === mainChatTabId || state.tabs[to]?.id === mainChatTabId) return state;
	if (from < 0 || to < 0 || to >= state.tabs.length || from === to) return state;
	const tabs = [...state.tabs];
	tabs.splice(to, 0, tabs.splice(from, 1)[0]);
	return { ...state, tabs };
}

export const fileTabId = (terminalId: string, path: string) =>
	JSON.stringify(['file', terminalId, path]);
