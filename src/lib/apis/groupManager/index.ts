import { WEBUI_API_BASE_URL } from '$lib/constants';

const request = async (token: string, path: string, options: RequestInit = {}) => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/group-manager${path}`, {
		...options,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
			...(options.headers ?? {})
		}
	});
	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		const error: any = new Error(body?.detail ?? 'Unable to access this group workspace.');
		error.status = response.status;
		throw error;
	}
	return response.json();
};

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

export const getGroupManagerGroups = (token: string) => request(token, '/groups');

export const getGroupManagerMembers = (token: string, groupId: string) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/members`);
export const addGroupManagerMembers = (token: string, groupId: string, userIds: string[]) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/members/add`, json({ user_ids: userIds }));
export const deleteGroupManagerMembers = (token: string, groupId: string, userIds: string[]) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/members/remove`,
		json({ user_ids: userIds })
	);

export const getGroupManagerAssets = (token: string, groupId: string, resourceType?: string) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/assets${resourceType ? `?resource_type=${encodeURIComponent(resourceType)}` : ''}`
	);
export const createGroupKnowledge = (
	token: string,
	groupId: string,
	data: { name: string; description?: string }
) => request(token, `/groups/${encodeURIComponent(groupId)}/assets/knowledge/create`, json(data));
export const updateGroupKnowledge = (token: string, groupId: string, id: string, data: object) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/assets/knowledge/${encodeURIComponent(id)}/update`,
		json(data)
	);
export const deleteGroupKnowledge = (token: string, groupId: string, id: string) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/assets/knowledge/${encodeURIComponent(id)}/delete`,
		{ method: 'DELETE' }
	);
export const createGroupPrompt = (token: string, groupId: string, data: object) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/assets/prompts/create`, json(data));
export const updateGroupPrompt = (token: string, groupId: string, id: string, data: object) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/assets/prompts/${encodeURIComponent(id)}/update`,
		json(data)
	);
export const deleteGroupPrompt = (token: string, groupId: string, id: string) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/assets/prompts/${encodeURIComponent(id)}/delete`,
		{ method: 'DELETE' }
	);

export const getGroupManagerSkills = (token: string, groupId: string) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/skills`);
export const createGroupSkill = (token: string, groupId: string, data: object) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/skills/create`, json(data));
export const updateGroupSkill = (token: string, groupId: string, id: string, data: object) =>
	request(
		token,
		`/groups/${encodeURIComponent(groupId)}/skills/${encodeURIComponent(id)}/update`,
		json(data)
	);
export const deleteGroupSkill = (token: string, groupId: string, id: string) =>
	request(token, `/groups/${encodeURIComponent(groupId)}/skills/${encodeURIComponent(id)}/delete`, {
		method: 'DELETE'
	});
