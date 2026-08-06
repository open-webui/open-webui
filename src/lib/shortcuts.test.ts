import { beforeEach, describe, expect, it } from 'vitest';
import {
	eventToChord,
	loadKeybindings,
	matchKeybinding,
	resetKeybindings,
	Shortcut
} from './shortcuts';

const key = (
	key: string,
	modifiers: Partial<Pick<KeyboardEvent, 'ctrlKey' | 'metaKey' | 'altKey' | 'shiftKey'>> = {}
) =>
	({
		key,
		ctrlKey: false,
		metaKey: false,
		altKey: false,
		shiftKey: false,
		...modifiers
	}) as KeyboardEvent;

describe('shortcuts', () => {
	beforeEach(() => {
		resetKeybindings();
	});

	it('normalizes ctrl to Cmd on non-Mac platforms', () => {
		expect(eventToChord(key('k', { ctrlKey: true }))).toBe('Cmd+K');
		expect(matchKeybinding(key('k', { ctrlKey: true }))).toBe(Shortcut.SEARCH);
	});

	it('loads saved bindings, including unassigned shortcuts', () => {
		loadKeybindings({
			[Shortcut.SEARCH]: 'Cmd+Shift+P',
			[Shortcut.NEW_CHAT]: ''
		});

		expect(matchKeybinding(key('k', { ctrlKey: true }))).toBeNull();
		expect(matchKeybinding(key('p', { ctrlKey: true, shiftKey: true }))).toBe(Shortcut.SEARCH);
		expect(matchKeybinding(key('o', { ctrlKey: true, shiftKey: true }))).toBeNull();
	});
});
