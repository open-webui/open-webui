import { afterEach, describe, expect, it, vi } from 'vitest';
import { addGroupManagerMembers, getGroupManagerAssets, getGroupManagerGroups } from './index';

describe('group manager API client', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('keeps member mutations group-scoped and sends only user ids', async () => {
		const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await addGroupManagerMembers('token', 'group/1', ['user-1']);

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/v1/group-manager/groups/group%2F1/members/add',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ user_ids: ['user-1'] })
			})
		);
	});

	it('passes the asset type filter without broad workspace endpoints', async () => {
		const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await getGroupManagerAssets('token', 'group-1', 'knowledge');

		expect(fetchMock.mock.calls[0][0]).toBe(
			'/api/v1/group-manager/groups/group-1/assets?resource_type=knowledge'
		);
	});

	it('uses the additive minimal group discovery endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await getGroupManagerGroups('token');

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/group-manager/groups');
	});
});
