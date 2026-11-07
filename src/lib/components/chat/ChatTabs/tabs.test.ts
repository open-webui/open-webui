import { describe, expect, it } from 'vitest';
import {
	activateTab,
	emptyTabs,
	mainChatTabId,
	openTab,
	openTabInSidePanel,
	panelPositions,
	setMainChatTab,
	splitTab,
	type PanelTab
} from './tabs';

const sideTab = (id: string): PanelTab => ({ id, kind: 'side', label: id });

describe('opening a tab in the side panel', () => {
	it('creates a right pane and keeps the main chat visible', () => {
		const initial = openTab(setMainChatTab(emptyTabs(), true), {
			id: 'files',
			kind: 'files',
			label: 'Files'
		});
		const state = openTabInSidePanel(initial, { ...sideTab('side-1'), initialPrompt: 'Hello' });
		const main = state.groups.find((group) => group.tabIds.includes(mainChatTabId))!;
		const side = state.groups.find((group) => group.tabIds.includes('side-1'))!;
		expect(state.groups).toHaveLength(2);
		expect(main.activeId).toBe(mainChatTabId);
		expect(main.tabIds).toContain('files');
		expect(state.activeId).toBe('side-1');
		expect(panelPositions(state.layout).groups[side.id].left).toBe(0.5);
		expect(state.tabs.find((tab) => tab.id === 'side-1')?.initialPrompt).toBe('Hello');
	});

	it('reuses the existing side pane when the main chat is focused', () => {
		let state = openTabInSidePanel(setMainChatTab(emptyTabs(), true), sideTab('side-1'));
		const sideGroupId = state.activeGroupId;
		const layout = state.layout;
		state = openTabInSidePanel(activateTab(state, mainChatTabId), sideTab('side-2'));
		expect(state.groups).toHaveLength(2);
		expect(state.layout).toEqual(layout);
		expect(state.activeGroupId).toBe(sideGroupId);
		expect(state.groups.find((group) => group.id === sideGroupId)?.tabIds).toEqual([
			'side-1',
			'side-2'
		]);
		expect(state.groups.find((group) => group.tabIds.includes(mainChatTabId))?.activeId).toBe(
			mainChatTabId
		);
	});

	it('uses the focused side pane when there are multiple splits', () => {
		let state = openTabInSidePanel(setMainChatTab(emptyTabs(), true), sideTab('side-1'));
		state = openTab(state, sideTab('side-2'));
		state = splitTab(state, 'side-2', state.activeGroupId, 'bottom');
		const sideGroupId = state.activeGroupId;
		const layout = state.layout;
		state = openTabInSidePanel(state, sideTab('side-3'));
		expect(state.groups).toHaveLength(3);
		expect(state.layout).toEqual(layout);
		expect(state.activeGroupId).toBe(sideGroupId);
		expect(state.activeId).toBe('side-3');
	});

	it('opens normally when the main chat is outside the tab layout', () => {
		const state = openTabInSidePanel(emptyTabs(), sideTab('side-1'));
		expect(state.groups).toHaveLength(1);
		expect(state.activeId).toBe('side-1');
	});
});
