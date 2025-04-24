import type { Settings } from '$lib/stores';
import { type Writable, get, writable } from 'svelte/store';
import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	updateSettings,
} from './settings';

const mocks = vi.hoisted(() => {
	return {
		stores: {
			settings: { } as Writable<Settings>,
		},
		api: {
			users: {
				updateUserSettings: vi.fn(),
			},
		},
	};
});

vi.mock('$lib/stores', async () => {
	mocks.stores.settings = writable({ chatDirection: 'LTR' });
	return mocks.stores;
});

vi.mock('$lib/apis/users', async () => {
	return mocks.api.users;
});


vi.stubGlobal('localStorage', { });

describe('settings', () => {
	const mockToken = 'mock-token';

	beforeEach(() => {
		localStorage.token = mockToken;
	});

	describe('updateSettings()', async () => {
		it('should update the settings store with the existing settings extended by the new settings', async () => {
			mocks.stores.settings.set({
				chatDirection: 'LTR' as const,
				conversationMode: true,
				speechAutoSend: true,
			});

			await updateSettings({
				speechAutoSend: false,
				responseAutoPlayback: false,
			} as Partial<Settings>);

			const expectedNewSettings: Partial<Settings> = {
				chatDirection: 'LTR' as const,
				speechAutoSend: false,
				responseAutoPlayback: false,
			};

			expect(get(mocks.stores.settings)).toEqual(expectedNewSettings);
			expect(mocks.api.users.updateUserSettings).toHaveBeenCalledWith(
				mockToken,
				{
					ui: expectedNewSettings
				}
			);
		});
	});
});
