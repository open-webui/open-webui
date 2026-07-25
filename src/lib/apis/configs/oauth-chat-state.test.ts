import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	initiateOAuthRedirect,
	isSafeOAuthReturnPath,
	PENDING_OAUTH_CHAT_STATE_VERSION
} from './index';

describe('isSafeOAuthReturnPath', () => {
	it('accepts same-origin relative paths', () => {
		expect(isSafeOAuthReturnPath('/')).toBe(true);
		expect(isSafeOAuthReturnPath('/c/abc123')).toBe(true);
		expect(isSafeOAuthReturnPath('/?tools=a,b&web-search=true')).toBe(true);
	});

	it('rejects protocol-relative paths', () => {
		expect(isSafeOAuthReturnPath('//evil.com')).toBe(false);
		expect(isSafeOAuthReturnPath('//evil.com/c/1')).toBe(false);
	});

	it('rejects absolute URLs and non-rooted values', () => {
		expect(isSafeOAuthReturnPath('https://evil.com')).toBe(false);
		expect(isSafeOAuthReturnPath('c/abc123')).toBe(false);
		expect(isSafeOAuthReturnPath('')).toBe(false);
	});

	it('rejects non-string values', () => {
		expect(isSafeOAuthReturnPath(undefined)).toBe(false);
		expect(isSafeOAuthReturnPath(null)).toBe(false);
		expect(isSafeOAuthReturnPath(42)).toBe(false);
		expect(isSafeOAuthReturnPath({})).toBe(false);
	});
});

describe('initiateOAuthRedirect snapshot', () => {
	const store = new Map<string, string>();

	beforeEach(() => {
		store.clear();
		vi.stubGlobal('sessionStorage', {
			getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
			setItem: (k: string, v: string) => void store.set(k, v),
			removeItem: (k: string) => void store.delete(k)
		});
		vi.stubGlobal('window', { open: vi.fn() });
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	const tool = { id: 'server:mcp', serverId: 'mcp', authType: 'mcp' as const };

	it('persists a versioned snapshot with the provided chat state', () => {
		initiateOAuthRedirect(tool, {
			selectedToolIds: ['t1', 't2'],
			selectedSkillIds: ['s1'],
			selectedFilterIds: ['f1'],
			webSearchEnabled: true,
			imageGenerationEnabled: false,
			codeInterpreterEnabled: true,
			prompt: 'draft text',
			returnTo: '/c/xyz'
		});

		const snap = JSON.parse(store.get('pendingOAuthChatState')!);
		expect(snap.version).toBe(PENDING_OAUTH_CHAT_STATE_VERSION);
		expect(snap.pendingOAuthToolId).toBe('server:mcp');
		expect(snap.selectedToolIds).toEqual(['t1', 't2']);
		expect(snap.selectedSkillIds).toEqual(['s1']);
		expect(snap.selectedFilterIds).toEqual(['f1']);
		expect(snap.webSearchEnabled).toBe(true);
		expect(snap.imageGenerationEnabled).toBe(false);
		expect(snap.codeInterpreterEnabled).toBe(true);
		expect(snap.prompt).toBe('draft text');
		expect(snap.returnTo).toBe('/c/xyz');
	});

	it('mirrors selected models to the one-shot selectedModels key, not the snapshot', () => {
		initiateOAuthRedirect(tool, { selectedModels: ['opus-4-8'], selectedToolIds: ['t1'] });

		expect(JSON.parse(store.get('selectedModels')!)).toEqual(['opus-4-8']);
		const snap = JSON.parse(store.get('pendingOAuthChatState')!);
		expect('selectedModels' in snap).toBe(false);
	});

	it('does not write selectedModels for empty or placeholder model selection', () => {
		initiateOAuthRedirect(tool, { selectedModels: [''] });
		expect(store.has('selectedModels')).toBe(false);

		initiateOAuthRedirect(tool, { selectedModels: [] });
		expect(store.has('selectedModels')).toBe(false);
	});

	it('defaults every field when chat state is omitted', () => {
		initiateOAuthRedirect(tool);
		const snap = JSON.parse(store.get('pendingOAuthChatState')!);
		expect(snap.selectedToolIds).toEqual([]);
		expect(snap.selectedSkillIds).toEqual([]);
		expect(snap.selectedFilterIds).toEqual([]);
		expect(snap.webSearchEnabled).toBe(false);
		expect(snap.imageGenerationEnabled).toBe(false);
		expect(snap.codeInterpreterEnabled).toBe(false);
		expect(snap.prompt).toBe('');
		expect(snap.returnTo).toBe('');
		expect(store.has('selectedModels')).toBe(false);
	});

	it('keeps the legacy pendingOAuthToolId key for backward compatibility', () => {
		initiateOAuthRedirect(tool);
		expect(store.get('pendingOAuthToolId')).toBe('server:mcp');
	});
});
