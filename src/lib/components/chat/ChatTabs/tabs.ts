import type { TerminalContext } from '$lib/types';
import type { TerminalConnection } from '$lib/apis/terminal';

export type PanelTabKind =
	| 'files'
	| 'file'
	| 'terminal'
	| 'browser'
	| 'artifacts'
	| 'preview'
	| 'voice'
	| 'comments';
export type PanelTab = {
	id: string;
	kind: PanelTabKind;
	label: string;
	terminalId?: string;
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

export const fileTabId = (terminalId: string, path: string) =>
	JSON.stringify(['file', terminalId, path]);
