import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
	applyPendingOAuthState,
	consumePendingOAuthState,
	savePendingOAuthState
} from './oauth-pending-state';

class SessionStorageStub {
	private store = new Map<string, string>();

	getItem(key: string) {
		return this.store.has(key) ? this.store.get(key)! : null;
	}

	setItem(key: string, value: string) {
		this.store.set(key, value);
	}

	removeItem(key: string) {
		this.store.delete(key);
	}
}

const originalSessionStorage = globalThis.sessionStorage;
let sessionStorageStub: SessionStorageStub;

beforeEach(() => {
	sessionStorageStub = new SessionStorageStub();
	Object.defineProperty(globalThis, 'sessionStorage', {
		value: sessionStorageStub,
		configurable: true
	});
});

afterEach(() => {
	if (originalSessionStorage === undefined) {
		Reflect.deleteProperty(globalThis, 'sessionStorage');
		return;
	}

	Object.defineProperty(globalThis, 'sessionStorage', {
		value: originalSessionStorage,
		configurable: true
	});
});

describe('oauth pending state helpers', () => {
	it('stores and restores tool + selected models for oauth redirects', () => {
		savePendingOAuthState({
			toolId: 'server:mcp:demo',
			selectedModels: ['model-a', 'model-b']
		});

		expect(sessionStorage.getItem('pendingOAuthToolId')).toBe('server:mcp:demo');
		expect(sessionStorage.getItem('pendingOAuthSelectedModels')).toBe(
			JSON.stringify(['model-a', 'model-b'])
		);

		expect(consumePendingOAuthState()).toEqual({
			toolId: 'server:mcp:demo',
			selectedModels: ['model-a', 'model-b']
		});

		expect(sessionStorage.getItem('pendingOAuthToolId')).toBeNull();
		expect(sessionStorage.getItem('pendingOAuthSelectedModels')).toBeNull();
	});

	it('ignores malformed selected-model snapshots', () => {
		sessionStorage.setItem('pendingOAuthToolId', 'server:mcp:demo');
		sessionStorage.setItem('pendingOAuthSelectedModels', '{bad json');

		expect(consumePendingOAuthState()).toEqual({
			toolId: 'server:mcp:demo',
			selectedModels: null
		});
	});

	it('restores the pending tool and filters restored models against available models', () => {
		expect(
			applyPendingOAuthState({
				availableModels: ['model-a', 'model-c'],
				selectedModels: ['model-z'],
				selectedToolIds: ['existing-tool'],
				pendingState: {
					toolId: 'server:mcp:demo',
					selectedModels: ['model-a', 'model-b']
				}
			})
		).toEqual({
			selectedModels: ['model-a'],
			selectedToolIds: ['existing-tool', 'server:mcp:demo']
		});
	});

	it('preserves the current selection when no pending oauth state exists', () => {
		expect(
			applyPendingOAuthState({
				availableModels: ['model-a'],
				selectedModels: ['model-a'],
				selectedToolIds: ['existing-tool'],
				pendingState: {
					toolId: 'existing-tool',
					selectedModels: null
				}
			})
		).toEqual({
			selectedModels: ['model-a'],
			selectedToolIds: ['existing-tool']
		});
	});
});
