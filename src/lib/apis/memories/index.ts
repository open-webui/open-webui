import { webuiApiClient } from '../clients';

interface Memory {
	id: string;
	content: string;
	[key: string]: unknown;
}

export const getMemories = async (token: string) =>
	webuiApiClient.get<Memory[]>('/memories/', { token });

export const addNewMemory = async (token: string, content: string) =>
	webuiApiClient.post('/memories/add', { content }, { token });

export const updateMemoryById = async (token: string, id: string, content: string) =>
	webuiApiClient.post(`/memories/${id}/update`, { content }, { token });

export const queryMemory = async (token: string, content: string) =>
	webuiApiClient.post('/memories/query', { content }, { token });

export const deleteMemoryById = async (token: string, id: string) =>
	webuiApiClient.del(`/memories/${id}`, null, { token });

export const deleteMemoriesByUserId = async (token: string) =>
	webuiApiClient.del('/memories/delete/user', null, { token });
