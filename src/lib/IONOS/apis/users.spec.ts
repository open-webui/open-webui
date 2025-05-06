import { describe, beforeEach, expect, it, vi } from 'vitest';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { deleteAccount } from '$lib/IONOS/apis/users';

const mocks = vi.hoisted(() => {
	return {
		fetch: vi.fn(),
	};
});

vi.stubGlobal('fetch', mocks.fetch);

describe('deleteAccount()', () => {
	const mockToken = 'mock-token';

	beforeEach(() => {
		mocks.fetch.mockImplementation(() => {
			return new Response('', { status: 500 });
		});
	});

	it('should DELETE /users/user/self and include the authorization header', async () => {
		mocks.fetch.mockImplementation(() => {
			return new Response('true', { status: 200 });
		});

		await deleteAccount(mockToken);

		expect(fetch).toHaveBeenCalledWith(`${WEBUI_API_BASE_URL}/users/user/self`, {
			method: 'DELETE',
			headers: {
				Authorization: `Bearer ${mockToken}`
			},
		});
	});

	it('should reject if the request failed', async () => {
		await expect(() => deleteAccount(mockToken)).rejects.toThrowError(new Error('Error deleting account: request failed'));
	});

	it('should reject if the request succeeed but with false', async () => {
		mocks.fetch.mockImplementation(() => {
			return new Response('false', { status: 200 });
		});

		await expect(() => deleteAccount(mockToken)).rejects.toThrowError(new Error('Error deleting account: delete failed'));
	});
});
