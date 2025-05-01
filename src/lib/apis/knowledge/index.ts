import { webuiApiClient } from '../clients';

interface Knowledge {
	id: string;
	name: string;
	description: string;
	data?: Record<string, unknown>;
	access_control?: null | Record<string, unknown>;
}

type KnowledgeUpdateForm = {
	name?: string;
	description?: string;
	data?: Record<string, unknown>;
	access_control?: null | Record<string, unknown>;
};

export const createNewKnowledge = async (
	token: string,
	name: string,
	description: string,
	accessControl: null | Record<string, unknown>
) => {
	return await webuiApiClient.post<Knowledge>(
		'/knowledge/create',
		{
			name,
			description,
			access_control: accessControl
		},
		{ token }
	);
};

export const getKnowledgeBases = async (token: string = '') => {
	return await webuiApiClient.get<Knowledge[]>('/knowledge/', { token });
};

export const getKnowledgeBaseList = async (token: string = '') => {
	return await webuiApiClient.get<Knowledge[]>('/knowledge/list', { token });
};

export const getKnowledgeById = async (token: string, id: string) => {
	return await webuiApiClient.get<Knowledge>(`/knowledge/${id}`, { token });
};

export const updateKnowledgeById = async (token: string, id: string, form: KnowledgeUpdateForm) => {
	const payload = {
		name: form?.name,
		description: form?.description,
		data: form?.data,
		access_control: form.access_control
	};
	return await webuiApiClient.post<Knowledge>(`/knowledge/${id}/update`, payload, { token });
};

export const addFileToKnowledgeById = async (token: string, id: string, fileId: string) => {
	return await webuiApiClient.post<Knowledge>(
		`/knowledge/${id}/file/add`,
		{ file_id: fileId },
		{ token }
	);
};

export const updateFileFromKnowledgeById = async (token: string, id: string, fileId: string) => {
	return await webuiApiClient.post<Knowledge>(
		`/knowledge/${id}/file/update`,
		{ file_id: fileId },
		{ token }
	);
};

export const removeFileFromKnowledgeById = async (token: string, id: string, fileId: string) => {
	return await webuiApiClient.post<Knowledge>(
		`/knowledge/${id}/file/remove`,
		{ file_id: fileId },
		{ token }
	);
};

export const resetKnowledgeById = async (token: string, id: string) => {
	return await webuiApiClient.post<Knowledge>(`/knowledge/${id}/reset`, {}, { token });
};

export const deleteKnowledgeById = async (token: string, id: string) => {
	return await webuiApiClient.del<Knowledge>(`/knowledge/${id}/delete`, null, { token });
};

export const reindexKnowledgeFiles = async (token: string) => {
	return await webuiApiClient.post('/knowledge/reindex', {}, { token });
};
