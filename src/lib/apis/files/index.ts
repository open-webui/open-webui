import { webuiApiClient } from '../clients';

interface FileData {
	id: string;
	name: string;
	[key: string]: unknown;
}

export const uploadFile = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);
	return webuiApiClient.post<FileData>('/files/', data, { token });
};

export const uploadDir = async (token: string) =>
	webuiApiClient.post('/files/upload/dir', {}, { token });

export const getFiles = async (token: string = '') =>
	webuiApiClient.get<FileData[]>('/files/', { token });

export const getFileById = async (token: string, id: string) =>
	webuiApiClient.get<FileData>(`/files/${id}`, { token });

export const updateFileDataContentById = async (token: string, id: string, content: string) =>
	webuiApiClient.post<FileData>(`/files/${id}/data/content/update`, { content }, { token });

export const getFileContentById = async (id: string) =>
	webuiApiClient.get<Blob>(`/files/${id}/content`, { withCredentials: true });

export const deleteFileById = async (token: string, id: string) =>
	webuiApiClient.del<FileData>(`/files/${id}`, null, { token });

export const deleteAllFiles = async (token: string) =>
	webuiApiClient.del('/files/all', null, { token });
