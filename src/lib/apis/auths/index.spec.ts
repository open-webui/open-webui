import { describe, beforeEach, expect, it, vi } from 'vitest';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { userSignOut } from '$lib/apis/auths';


const mocks = vi.hoisted(() => {
	return {
		fetch: vi.fn(),
	};
});

vi.stubGlobal('fetch', mocks.fetch);

describe('userSignOut()', () => {
	beforeEach(() => {
		mocks.fetch.mockImplementation(() => {
			return new Response('', { status: 500 });
		});
	});

	it('should GET /auths/signout and include credentials', async () => {
		try {
			await userSignOut();
		} catch { /* expected */ }

		expect(fetch).toHaveBeenCalledWith(
			`${WEBUI_API_BASE_URL}/auths/signout`,
			{
				method: 'GET',
				credentials: 'include',
			},
		);
	});

	it('should not throw on OK response', async () => {
		mocks.fetch.mockImplementation(() => {
			return new Response('{ "status": true }', { status: 200 });
		});

		await expect(userSignOut()).resolves.toBe(undefined);
	});

	describe("failed", () => {
		it('should throw generic error', async () => {
			mocks.fetch.mockImplementation(() => {
				return new Response('', { status: 404, statusText: 'not found' });
			});

			await expect(userSignOut()).rejects.toThrowError('Request failed with no details: 404 not found');
		});

		it('should throw error containing detail', async () => {
			mocks.fetch.mockImplementation(() => {
				return new Response('{ "detail": "something wrong" }', { status: 500, headers: { 'Content-Type': 'application/json' } });
			});

			await expect(userSignOut()).rejects.toThrowError('something wrong');
		});

		it('should throw generic error with missing detail', async () => {
			mocks.fetch.mockImplementation(() => {
				return new Response('{ }', { status: 500, statusText: 'server error', headers: { 'Content-Type': 'application/json' } });
			});

			await expect(userSignOut()).rejects.toThrowError('Request failed with no details: 500 server error');
		});
	});
});
