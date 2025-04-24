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
		const initialSettings: Settings = {
			chatDirection: 'LTR' as const,
			conversationMode: true,
			speechAutoSend: true,
		};

		beforeEach(() => {
			mocks.stores.settings.set(initialSettings);
		});

		it('should update the settings store with the existing settings extended by the new settings', async () => {
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

		describe('if updateUserSettings() fails', () => {
			it('should not update the settings store', async () => {
				mocks.api.users.updateUserSettings.mockImplementation(() => Promise.reject(new Error('Some error')));

				try {
					await updateSettings({
						speechAutoSend: false,
						responseAutoPlayback: false,
					});
				} catch { /* not relevant for this test */ }

				expect(get(mocks.stores.settings)).toEqual(initialSettings);
			});
			it('should not update the settings store', async () => {
				mocks.api.users.updateUserSettings.mockImplementation(() => Promise.reject(new Error('Some error')));

				const newSettings: Partial<Settings> = {
					speechAutoSend: false,
					responseAutoPlayback: false,
				};

				expect(() => updateSettings(newSettings)).rejects.toThrowError(new Error('Some error'));
			});
		});
	});
});
