import { afterEach, describe, expect, it, vi } from 'vitest';
import { deleteCustomRole, updateCustomRole } from './index';

describe('custom role lifecycle API client', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('deletes a role through the dedicated role endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(new Response('true', { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await deleteCustomRole('token', 'role-1');

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/v1/custom-roles/role-1',
			expect.objectContaining({ method: 'DELETE' })
		);
	});

	it('uses active updates for the accessible lifecycle toggle', async () => {
		const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await updateCustomRole('token', 'role-1', { active: false });

		expect(fetchMock.mock.calls[0][1]).toEqual(
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ active: false })
			})
		);
	});
});
