import { webuiApiClient } from '../clients';

// Interfaces
export interface Group extends Record<string, unknown> {
	id?: string;
	name: string;
}

// Group Operations
export const createNewGroup = async (token: string, group: Group) =>
	webuiApiClient.post('/groups/create', group, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to create new group';
	});

export const getGroups = async (token = '') =>
	webuiApiClient.get<Group[]>('/groups/', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get groups';
	});

export const getGroupById = async (token: string, id: string) =>
	webuiApiClient.get<Group>(`/groups/id/${id}`, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get group';
	});

export const updateGroupById = async (token: string, id: string, group: Group) =>
	webuiApiClient.post(`/groups/id/${id}/update`, group, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update group';
	});

export const deleteGroupById = async (token: string, id: string) =>
	webuiApiClient.del(`/groups/id/${id}/delete`, undefined, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to delete group';
	});
