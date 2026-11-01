import { describe, expect, it } from 'vitest';
import { activateTab, emptyTabs, fileTabId, openTab, removeTab, type PanelTab } from './tabs';

const tab = (id: string, kind: PanelTab['kind'] = 'file'): PanelTab => ({ id, kind, label: id });

describe('chat panel tabs', () => {
	it('reuses an open file and keeps files from different terminals separate', () => {
		const a = tab(fileTabId('server-a', '/readme.md'));
		const b = tab(fileTabId('server-b', '/readme.md'));
		let state = openTab(openTab(emptyTabs(), a), b);
		state = openTab(state, a);
		expect(state.tabs).toHaveLength(2);
		expect(state.activeId).toBe(a.id);
	});
	it('keeps independent shells and returns to the most recently used tab on close', () => {
		let state = openTab(
			openTab(openTab(emptyTabs(), tab('files', 'files')), tab('shell-1', 'terminal')),
			tab('shell-2', 'terminal')
		);
		state = activateTab(state, 'files');
		state = activateTab(state, 'shell-2');
		state = removeTab(state, 'shell-2');
		expect(state.activeId).toBe('files');
		expect(state.tabs.map((item) => item.id)).toEqual(['files', 'shell-1']);
	});
	it('closes a feature view without automatically reopening it and can reopen it explicitly', () => {
		let state = openTab(emptyTabs(), tab('artifacts', 'artifacts'));
		state = removeTab(state, 'artifacts');
		expect(state).toEqual(emptyTabs());
		state = openTab(state, tab('artifacts', 'artifacts'));
		expect(state.activeId).toBe('artifacts');
	});
	it('closing an inactive tab leaves the active tab selected', () => {
		const state = removeTab(openTab(openTab(emptyTabs(), tab('a')), tab('b')), 'a');
		expect(state.activeId).toBe('b');
		expect(state.history).toEqual([]);
	});
});
