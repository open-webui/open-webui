import { webuiApiClient } from '../clients';

interface Model {
	id: string;
	[key: string]: unknown;
}

export const getModels = async (token: string = '') =>
	webuiApiClient.get<Model[]>('/models/', { token });

export const getBaseModels = async (token: string = '') =>
	webuiApiClient.get<Model[]>('/models/base', { token });

export const createNewModel = async (token: string, model: Record<string, unknown>) =>
	webuiApiClient.post('/models/create', model, { token });

export const getModelById = async (token: string, id: string) =>
	webuiApiClient.get(`/models/model?${new URLSearchParams({ id })}`, { token });

export const toggleModelById = async (token: string, id: string) =>
	webuiApiClient.post(`/models/model/toggle?${new URLSearchParams({ id })}`, {}, { token });

export const updateModelById = async (token: string, id: string, model: Record<string, unknown>) =>
	webuiApiClient.post(`/models/model/update?${new URLSearchParams({ id })}`, model, { token });

export const deleteModelById = async (token: string, id: string) =>
	webuiApiClient.del(`/models/model/delete?${new URLSearchParams({ id })}`, null, { token });

export const deleteAllModels = async (token: string) =>
	webuiApiClient.del('/models/delete/all', null, { token });
