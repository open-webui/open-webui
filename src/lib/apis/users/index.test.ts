import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/constants', () => ({
	WEBUI_API_BASE_URL: 'http://test/api/v1'
}));

vi.mock('$lib/utils', () => ({
	getUserPosition: vi.fn()
}));

const response = (body: unknown, ok = true) =>
	({
		ok,
		json: vi.fn().mockResolvedValue(body)
	}) as unknown as Response;

const loadUsersApi = async () => import('./index');

describe('user settings hydration guard', () => {
	beforeEach(() => {
		vi.resetModules();
		vi.stubGlobal('fetch', vi.fn());
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
	});

	afterEach(() => {
		vi.restoreAllMocks();
		vi.unstubAllGlobals();
	});

	it('blocks full UI settings updates before settings are loaded', async () => {
		const { updateUserSettings } = await loadUsersApi();

		await expect(updateUserSettings('token-a', { ui: {} })).rejects.toThrow(
			'Cannot update user interface settings before they have been loaded.'
		);
		expect(fetch).not.toHaveBeenCalled();
	});

	it('keeps UI settings updates blocked after a failed load', async () => {
		vi.mocked(fetch).mockResolvedValueOnce(response({ detail: 'settings unavailable' }, false));
		const { getUserSettings, updateUserSettings } = await loadUsersApi();

		await expect(getUserSettings('token-a')).rejects.toBe('settings unavailable');
		await expect(updateUserSettings('token-a', { ui: { theme: 'dark' } })).rejects.toThrow(
			'Cannot update user interface settings before they have been loaded.'
		);
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('keeps UI settings updates blocked after a network failure', async () => {
		vi.mocked(fetch).mockRejectedValueOnce(new Error('network unavailable'));
		const { getUserSettings, updateUserSettings } = await loadUsersApi();

		await expect(getUserSettings('token-a')).resolves.toBeNull();
		await expect(updateUserSettings('token-a', { ui: { theme: 'dark' } })).rejects.toThrow(
			'Cannot update user interface settings before they have been loaded.'
		);
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('allows UI settings updates after a successful load with no saved settings', async () => {
		vi.mocked(fetch)
			.mockResolvedValueOnce(response(null))
			.mockResolvedValueOnce(response({ ui: { theme: 'dark' } }));
		const { getUserSettings, updateUserSettings } = await loadUsersApi();

		await expect(getUserSettings('token-a')).resolves.toBeNull();
		await expect(updateUserSettings('token-a', { ui: { theme: 'dark' } })).resolves.toEqual({
			ui: { theme: 'dark' }
		});
		expect(fetch).toHaveBeenCalledTimes(2);
	});

	it('does not reuse hydration from a different token', async () => {
		vi.mocked(fetch).mockResolvedValueOnce(response({ ui: { theme: 'dark' } }));
		const { getUserSettings, updateUserSettings } = await loadUsersApi();

		await getUserSettings('token-a');
		await expect(updateUserSettings('token-b', { ui: { theme: 'light' } })).rejects.toThrow(
			'Cannot update user interface settings before they have been loaded.'
		);
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('blocks UI settings updates after a later refresh fails', async () => {
		vi.mocked(fetch)
			.mockResolvedValueOnce(response({ ui: { theme: 'dark' } }))
			.mockResolvedValueOnce(response({ detail: 'settings unavailable' }, false));
		const { getUserSettings, updateUserSettings } = await loadUsersApi();

		await getUserSettings('token-a');
		await expect(getUserSettings('token-a')).rejects.toBe('settings unavailable');
		await expect(updateUserSettings('token-a', { ui: { theme: 'light' } })).rejects.toThrow(
			'Cannot update user interface settings before they have been loaded.'
		);
		expect(fetch).toHaveBeenCalledTimes(2);
	});

	it('allows top-level partial updates that cannot replace UI settings', async () => {
		vi.mocked(fetch).mockResolvedValueOnce(response({ keybindings: { search: 'Cmd+K' } }));
		const { updateUserSettings } = await loadUsersApi();

		await expect(
			updateUserSettings('token-a', { keybindings: { search: 'Cmd+K' } })
		).resolves.toEqual({ keybindings: { search: 'Cmd+K' } });
		expect(fetch).toHaveBeenCalledTimes(1);
	});
});
